/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Native platform sensor driver. Biometric decisions come only from the
 * root-only secure-firmware bridge; this library carries opaque references.
 */
#include "drivers_api.h"
#include <pwd.h>
#include <signal.h>
#include <unistd.h>

#ifdef AURA_BRIDGE_TEST_ONLY
#define AURA_BRIDGE_PATH "/var/tmp/aura-libfprint-operations/mock-bridge.py"
#else
#define AURA_BRIDGE_PATH "/opt/aura-fprint-candidate/aura_fprint_bridge.py"
#endif

typedef struct _FpiDeviceAuraFpc {
  FpDevice parent;
  GSubprocess *process;
  GString *pending;
  GPtrArray *records;
  char *result;
  GError *error;
  gboolean eof, waited, cancelled;
  guint timeout, kill_timeout, total, stages;
} FpiDeviceAuraFpc;
typedef struct _FpiDeviceAuraFpcClass { FpDeviceClass parent; } FpiDeviceAuraFpcClass;
GType fpi_device_aura_fpc_get_type (void);
G_DEFINE_TYPE (FpiDeviceAuraFpc, fpi_device_aura_fpc, FP_TYPE_DEVICE)

static const FpIdEntry ids[] = {
  { .udev_types = FPI_DEVICE_UDEV_SUBTYPE_PLATFORM,
    .platform_compatible = "razer,aura-fpc-resources", .platform_driver = "aura-fpc-resources" },
  { .udev_types = 0 }
};

static gboolean valid_account (guint uid, const char *name, guint finger)
{
  if (uid < 1000 || uid == G_MAXUINT || finger < 1 || finger > 10 || !name ||
      !g_regex_match_simple ("^[A-Za-z_][A-Za-z0-9_.-]{0,63}$", name, 0, 0)) return FALSE;
  struct passwd *account = getpwnam (name);
  return account && account->pw_uid == uid;
}

static gboolean reference (FpPrint *print, guint *uid, guint *finger, char **name, char **token)
{
  g_autoptr(GVariant) data = NULL;
  guint version;
  const char *user, *id;
  g_object_get (print, "fpi-data", &data, NULL);
  if (!data || !g_variant_is_of_type (data, G_VARIANT_TYPE ("(uuuss)"))) return FALSE;
  g_variant_get (data, "(uuu&s&s)", &version, uid, finger, &user, &id);
  if (version != 1 || !valid_account (*uid, user, *finger) ||
      g_strcmp0 (fp_print_get_username (print), user) || fp_print_get_finger (print) != *finger ||
      !g_regex_match_simple ("^[0-9a-f]{32}$", id, 0, 0)) return FALSE;
  *name = g_strdup (user); *token = g_strdup (id);
  return TRUE;
}

static FpPrint *parse_record (FpDevice *device, const char *line)
{
  g_auto(GStrv) parts = g_strsplit (line, " ", -1);
  if (g_strv_length (parts) != 5 || strcmp (parts[0], "RECORD") ||
      !g_regex_match_simple ("^[1-9][0-9]{0,9}$", parts[1], 0, 0) ||
      !g_regex_match_simple ("^([1-9]|10)$", parts[3], 0, 0) ||
      !g_regex_match_simple ("^[0-9a-f]{32}$", parts[4], 0, 0)) return NULL;
  guint64 wide = g_ascii_strtoull (parts[1], NULL, 10);
  guint finger = g_ascii_strtoull (parts[3], NULL, 10);
  if (wide >= G_MAXUINT || !valid_account (wide, parts[2], finger)) return NULL;
  FpPrint *print = fp_print_new (device);
  fpi_print_set_type (print, FPI_PRINT_RAW);
  fpi_print_set_device_stored (print, TRUE);
  fp_print_set_username (print, parts[2]);
  fp_print_set_finger (print, finger);
  g_object_set (print, "fpi-data", g_variant_new ("(uuuss)", 1u, (guint) wide, finger, parts[2], parts[4]), NULL);
  return print;
}

static gboolean force_stop (gpointer data)
{
  FpiDeviceAuraFpc *self = data;
  self->kill_timeout = 0;
  if (self->process && !self->waited) g_subprocess_force_exit (self->process);
  return G_SOURCE_REMOVE;
}

static void stop_worker (FpiDeviceAuraFpc *self)
{
  if (self->process && !self->waited) g_subprocess_send_signal (self->process, SIGTERM);
  if (!self->kill_timeout) self->kill_timeout = g_timeout_add_seconds (10, force_stop, self);
}

static void protocol_error (FpiDeviceAuraFpc *self)
{
  if (!self->error) self->error = fpi_device_error_new (FP_DEVICE_ERROR_PROTO);
  stop_worker (self);
}

static void finish (FpiDeviceAuraFpc *self)
{
  if (!self->waited || !self->eof) return;
  FpDevice *device = FP_DEVICE (self);
  FpiDeviceAction action = fpi_device_get_current_action (device);
  g_autoptr(GError) error = g_steal_pointer (&self->error);
  g_autoptr(GPtrArray) records = g_steal_pointer (&self->records);
  g_autofree char *result = g_steal_pointer (&self->result);
  if (self->timeout) { g_source_remove (self->timeout); self->timeout = 0; }
  if (self->kill_timeout) { g_source_remove (self->kill_timeout); self->kill_timeout = 0; }
  if (self->cancelled || !g_strcmp0 (result, "cancelled")) {
    g_clear_error (&error);
    error = g_error_new_literal (G_IO_ERROR, G_IO_ERROR_CANCELLED, "Fingerprint operation cancelled");
  } else if (!error && (!g_subprocess_get_successful (self->process) || !result))
    error = fpi_device_error_new (FP_DEVICE_ERROR_GENERAL);
  if (!error && !strcmp (result, "not-enrolled")) error = fpi_device_error_new (FP_DEVICE_ERROR_DATA_NOT_FOUND);
  if (!error && !strcmp (result, "retry")) error = fpi_device_error_new (FP_DEVICE_ERROR_BUSY);
  if (!error && !strcmp (result, "error")) error = fpi_device_error_new (FP_DEVICE_ERROR_GENERAL);
  g_clear_object (&self->process);
  g_string_free (self->pending, TRUE); self->pending = NULL;
  fpi_device_report_finger_status (device, FP_FINGER_STATUS_NONE);
  if (!error) {
    const char *expected = action == FPI_DEVICE_ACTION_OPEN ? "ready" :
      action == FPI_DEVICE_ACTION_ENROLL ? "enrolled" : action == FPI_DEVICE_ACTION_LIST ? "listed" :
      action == FPI_DEVICE_ACTION_DELETE ? "deleted" : NULL;
    if ((expected && strcmp (result, expected)) ||
        (action == FPI_DEVICE_ACTION_VERIFY && strcmp (result, "match") && strcmp (result, "no-match")))
      error = fpi_device_error_new (FP_DEVICE_ERROR_PROTO);
    if (!error && action == FPI_DEVICE_ACTION_ENROLL) {
      FpPrint *requested;
      fpi_device_get_enroll_data (device, &requested);
      if (records->len != 1 ||
          g_strcmp0 (fp_print_get_username (requested), fp_print_get_username (g_ptr_array_index (records, 0))) ||
          fp_print_get_finger (requested) != fp_print_get_finger (g_ptr_array_index (records, 0)))
        error = fpi_device_error_new (FP_DEVICE_ERROR_PROTO);
    }
  }
  if (error) { fpi_device_action_error (device, g_steal_pointer (&error)); return; }
  switch (action) {
  case FPI_DEVICE_ACTION_OPEN: fpi_device_open_complete (device, NULL); break;
  case FPI_DEVICE_ACTION_LIST: fpi_device_list_complete (device, g_steal_pointer (&records), NULL); break;
  case FPI_DEVICE_ACTION_DELETE: fpi_device_delete_complete (device, NULL); break;
  case FPI_DEVICE_ACTION_ENROLL:
    fpi_device_enroll_progress (device, 20, NULL, NULL);
    fpi_device_enroll_complete (device, g_object_ref (g_ptr_array_index (records, 0)), NULL); break;
  case FPI_DEVICE_ACTION_VERIFY:
    fpi_device_verify_report (device, !strcmp (result, "match") ? FPI_MATCH_SUCCESS : FPI_MATCH_FAIL, NULL, NULL);
    fpi_device_verify_complete (device, NULL); break;
  case FPI_DEVICE_ACTION_NONE: case FPI_DEVICE_ACTION_PROBE: case FPI_DEVICE_ACTION_CLOSE:
  case FPI_DEVICE_ACTION_IDENTIFY: case FPI_DEVICE_ACTION_CAPTURE: case FPI_DEVICE_ACTION_CLEAR_STORAGE:
    g_assert_not_reached ();
  }
}

static void parse_line (FpiDeviceAuraFpc *self, const char *line)
{
  FpDevice *device = FP_DEVICE (self);
  FpiDeviceAction action = fpi_device_get_current_action (device);
  if (self->error || self->cancelled) return;
  if (self->result) { protocol_error (self); return; }
  if (g_str_has_prefix (line, "RESULT ")) {
    const char *value = line + 7;
    if (!g_regex_match_simple ("^(ready|listed|deleted|enrolled|match|no-match|not-enrolled|retry|cancelled|error)$", value, 0, 0))
      { protocol_error (self); return; }
    self->result = g_strdup (value); return;
  }
  if (g_str_has_prefix (line, "RECORD ") &&
      (action == FPI_DEVICE_ACTION_LIST || action == FPI_DEVICE_ACTION_ENROLL)) {
    FpPrint *print = parse_record (device, line);
    if (!print || self->records->len >= 100) { g_clear_object (&print); protocol_error (self); return; }
    for (guint i = 0; i < self->records->len; i++) {
      FpPrint *other = g_ptr_array_index (self->records, i);
      if (!g_strcmp0 (fp_print_get_username (print), fp_print_get_username (other)) &&
          fp_print_get_finger (print) == fp_print_get_finger (other)) {
        g_object_unref (print); protocol_error (self); return;
      }
    }
    g_ptr_array_add (self->records, print); return;
  }
  if (!strcmp (line, "TOUCH") && (action == FPI_DEVICE_ACTION_VERIFY || action == FPI_DEVICE_ACTION_ENROLL)) {
    fpi_device_report_finger_status (device, FP_FINGER_STATUS_NEEDED); return;
  }
  if (action == FPI_DEVICE_ACTION_ENROLL && g_regex_match_simple ("^SAMPLE [0-6] [0-9]{1,3}$", line, 0, 0)) {
    guint status = line[7] - '0';
    guint remaining = g_ascii_strtoull (line + 9, NULL, 10);
    if (remaining > 100) { protocol_error (self); return; }
    if (status == 1 || status == 0) {
      guint completed = MIN (19, 20 - MIN (20, remaining));
      if (completed > self->stages) { self->stages = completed; fpi_device_enroll_progress (device, completed, NULL, NULL); }
    } else fpi_device_enroll_progress (device, self->stages, NULL, fpi_device_retry_new (FP_DEVICE_RETRY_GENERAL));
    return;
  }
  protocol_error (self);
}

static void read_output (GObject *source, GAsyncResult *result, gpointer data)
{
  FpiDeviceAuraFpc *self = data;
  g_autoptr(GError) error = NULL;
  g_autoptr(GBytes) bytes = g_input_stream_read_bytes_finish (G_INPUT_STREAM (source), result, &error);
  gsize length = 0;
  const char *chunk = bytes ? g_bytes_get_data (bytes, &length) : NULL;
  if (error || !length) {
    self->eof = TRUE;
    if (error || self->pending->len) protocol_error (self);
    finish (self); g_object_unref (self); return;
  }
  self->total += length;
  if (self->total > 65536 || memchr (chunk, 0, length)) protocol_error (self);
  if (!self->error && !self->cancelled) {
    g_string_append_len (self->pending, chunk, length);
    char *newline;
    while ((newline = strchr (self->pending->str, '\n'))) {
      gsize size = newline - self->pending->str;
      if (size > 255) { protocol_error (self); break; }
      *newline = 0; parse_line (self, self->pending->str);
      g_string_erase (self->pending, 0, size + 1);
    }
    if (self->pending->len > 255) protocol_error (self);
  }
  g_input_stream_read_bytes_async (G_INPUT_STREAM (source), 4096, G_PRIORITY_DEFAULT, NULL, read_output, self);
}

static void wait_done (GObject *source, GAsyncResult *result, gpointer data)
{
  FpiDeviceAuraFpc *self = data;
  g_autoptr(GError) error = NULL;
  if (!g_subprocess_wait_finish (G_SUBPROCESS (source), result, &error)) protocol_error (self);
  self->waited = TRUE;
  finish (self); g_object_unref (self);
}

static gboolean timed_out (gpointer data)
{
  FpiDeviceAuraFpc *self = data;
  self->timeout = 0;
  if (!self->error) self->error = g_error_new_literal (G_IO_ERROR, G_IO_ERROR_TIMED_OUT, "Fingerprint operation timed out");
  stop_worker (self);
  return G_SOURCE_REMOVE;
}

static void start (FpDevice *device, const char *operation, FpPrint *print, gboolean enrolling)
{
  FpiDeviceAuraFpc *self = (FpiDeviceAuraFpc *) device;
  g_autofree char *name = NULL, *token = NULL, *uid_text = NULL, *finger_text = NULL;
  g_autoptr(GSubprocessLauncher) launcher = NULL;
  g_autoptr(GError) error = NULL;
  guint uid = 0, finger = 0;
  if (geteuid ()) { fpi_device_action_error (device, fpi_device_error_new (FP_DEVICE_ERROR_NOT_SUPPORTED)); return; }
  if (print) {
    if (enrolling) {
      name = g_strdup (fp_print_get_username (print)); finger = fp_print_get_finger (print);
      struct passwd *account = name ? getpwnam (name) : NULL;
      if (account) uid = account->pw_uid;
      if (!valid_account (uid, name, finger)) goto invalid;
    } else if (!reference (print, &uid, &finger, &name, &token)) goto invalid;
    uid_text = g_strdup_printf ("%u", uid); finger_text = g_strdup_printf ("%u", finger);
  }
  const char *argv[] = {"/usr/bin/python3", "-I", AURA_BRIDGE_PATH, operation,
                        uid_text, name, finger_text, token, NULL};
  launcher = g_subprocess_launcher_new (G_SUBPROCESS_FLAGS_STDOUT_PIPE | G_SUBPROCESS_FLAGS_STDERR_SILENCE);
  char path_env[] = "PATH=/usr/sbin:/usr/bin:/sbin:/bin", lang_env[] = "LANG=C.UTF-8";
  char *environment[] = {path_env, lang_env, NULL};
  g_subprocess_launcher_set_environ (launcher, environment);
  self->process = g_subprocess_launcher_spawnv (launcher, argv, &error);
  if (!self->process) { fpi_device_action_error (device, g_steal_pointer (&error)); return; }
  self->pending = g_string_new (NULL); self->records = g_ptr_array_new_with_free_func (g_object_unref);
  self->eof = self->waited = self->cancelled = FALSE; self->total = self->stages = 0;
  self->timeout = g_timeout_add_seconds (enrolling ? 340 : 85, timed_out, self);
  g_input_stream_read_bytes_async (g_subprocess_get_stdout_pipe (self->process), 4096, G_PRIORITY_DEFAULT, NULL, read_output, g_object_ref (self));
  g_subprocess_wait_async (self->process, NULL, wait_done, g_object_ref (self));
  return;
invalid:
  fpi_device_action_error (device, fpi_device_error_new (FP_DEVICE_ERROR_DATA_INVALID));
}

static void probe (FpDevice *device)
{
  const char *path = fpi_device_get_udev_data (device, FPI_DEVICE_UDEV_SUBTYPE_PLATFORM);
  if (!path || !g_path_is_absolute (path)) {
    fpi_device_probe_complete (device, NULL, NULL, fpi_device_error_new (FP_DEVICE_ERROR_NOT_SUPPORTED)); return;
  }
  fpi_device_probe_complete (device, "aura-fpc-qsee-v1", "Razer Phone 2 fingerprint sensor", NULL);
}
static void open_device (FpDevice *device) { start (device, "ready", NULL, FALSE); }
static void close_device (FpDevice *device) { fpi_device_close_complete (device, NULL); }
static void list_prints (FpDevice *device) { start (device, "list", NULL, FALSE); }
static void enroll (FpDevice *device) { FpPrint *print; fpi_device_get_enroll_data (device, &print); start (device, "enroll", print, TRUE); }
static void verify (FpDevice *device) { FpPrint *print; fpi_device_get_verify_data (device, &print); start (device, "verify", print, FALSE); }
static void delete_print (FpDevice *device) { FpPrint *print; fpi_device_get_delete_data (device, &print); start (device, "delete", print, FALSE); }
static void cancel (FpDevice *device) { FpiDeviceAuraFpc *self = (FpiDeviceAuraFpc *) device; self->cancelled = TRUE; stop_worker (self); }
static void fpi_device_aura_fpc_init (FpiDeviceAuraFpc *self) { (void) self; }
static void fpi_device_aura_fpc_class_init (FpiDeviceAuraFpcClass *klass)
{
  FpDeviceClass *device = FP_DEVICE_CLASS (klass);
  device->id = "aura_fpc"; device->full_name = "Razer Phone 2 Qualcomm TEE fingerprint sensor";
  device->type = FP_DEVICE_TYPE_UDEV; device->id_table = ids; device->scan_type = FP_SCAN_TYPE_PRESS;
  device->nr_enroll_stages = 20;
  device->probe = probe; device->open = open_device; device->close = close_device;
  device->enroll = enroll; device->verify = verify; device->list = list_prints; device->delete = delete_print; device->cancel = cancel;
  fpi_device_class_auto_initialize_features (device);
}
