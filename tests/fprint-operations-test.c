/* SPDX-License-Identifier: MIT */
#include <libfprint/fprint.h>
#include <string.h>

static guint progress_calls, retries, last_stage, match_calls;
static void progress (FpDevice *device, gint completed, FpPrint *print, gpointer data, GError *error)
{
  (void) device; (void) print; (void) data;
  g_assert_cmpint (completed, >=, last_stage); g_assert_cmpint (completed, <=, 20);
  last_stage = completed; progress_calls++;
  if (error) { g_assert_cmpuint (error->domain, ==, FP_DEVICE_RETRY); retries++; }
}
static void match_report (FpDevice *device, FpPrint *match, FpPrint *print, gpointer data, GError *error)
{
  (void) device; (void) match; (void) print; (void) data; (void) error;
  match_calls++;
}
static gboolean cancel_later (gpointer data) { g_cancellable_cancel (data); return G_SOURCE_REMOVE; }

int main (int argc, char **argv)
{
  g_assert_cmpint (argc, ==, 2);
  const char *scenario = argv[1];
  g_autoptr(FpContext) context = fp_context_new ();
  GPtrArray *devices = fp_context_get_devices (context);
  g_assert_cmpuint (devices->len, ==, 1);
  FpDevice *device = g_ptr_array_index (devices, 0);
  g_autoptr(GError) error = NULL;
  gboolean opened = fp_device_open_sync (device, NULL, &error);
  if (!strcmp (scenario, "open-error")) { g_assert_false (opened); g_assert_nonnull (error); return 0; }
  g_assert_no_error (error); g_assert_true (opened);
  g_autoptr(GPtrArray) prints = fp_device_list_prints_sync (device, NULL, &error);
  if (g_str_has_prefix (scenario, "list-")) {
    g_assert_null (prints); g_assert_nonnull (error); g_clear_error (&error);
  } else {
    g_assert_no_error (error); g_assert_cmpuint (prints->len, ==, 1);
    FpPrint *print = g_ptr_array_index (prints, 0);
    g_assert_cmpstr (fp_print_get_username (print), ==, "nobody");
    g_assert_cmpint (fp_print_get_finger (print), ==, 2);
    if (g_str_has_prefix (scenario, "verify-")) {
      g_autoptr(GCancellable) cancel = g_cancellable_new ();
      if (!strcmp (scenario, "verify-cancel")) g_timeout_add (150, cancel_later, cancel);
      if (!strcmp (scenario, "verify-wrong-metadata")) fp_print_set_username (print, "root");
      if (!strcmp (scenario, "verify-wrong-version")) g_object_set (print, "fpi-data", g_variant_new ("(uuuss)", 99u, 65534u, 2u, "nobody", "0123456789abcdef0123456789abcdef"), NULL);
      gboolean match = FALSE;
      gboolean success = fp_device_verify_sync (device, print, cancel, match_report, NULL, &match, NULL, &error);
      if (!strcmp (scenario, "verify-match") || !strcmp (scenario, "verify-no-match")) {
        g_assert_no_error (error); g_assert_true (success); g_assert_cmpuint (match_calls, ==, 1);
        g_assert_cmpint (match, ==, !strcmp (scenario, "verify-match"));
      } else {
        g_assert_false (success); g_assert_nonnull (error); g_assert_cmpuint (match_calls, ==, 0);
        if (!strcmp (scenario, "verify-cancel")) g_assert_error (error, G_IO_ERROR, G_IO_ERROR_CANCELLED);
        if (!strcmp (scenario, "verify-stale")) g_assert_error (error, FP_DEVICE_ERROR, FP_DEVICE_ERROR_DATA_NOT_FOUND);
        g_clear_error (&error);
      }
    } else if (g_str_has_prefix (scenario, "enroll-")) {
      FpPrint *requested = fp_print_new (device);
      fp_print_set_username (requested, "nobody"); fp_print_set_finger (requested, 3);
      g_autoptr(FpPrint) enrolled = fp_device_enroll_sync (device, requested, NULL, progress, NULL, &error);
      if (!strcmp (scenario, "enroll-good")) {
        g_assert_no_error (error); g_assert_nonnull (enrolled); g_assert_cmpuint (last_stage, ==, 20);
        g_assert_cmpuint (progress_calls, >=, 3); g_assert_cmpuint (retries, ==, 1);
        g_assert_cmpint (fp_print_get_finger (enrolled), ==, 3);
      } else { g_assert_null (enrolled); g_assert_nonnull (error); g_clear_error (&error); }
    } else if (!strcmp (scenario, "delete-good")) {
      g_assert_true (fp_device_delete_print_sync (device, print, NULL, &error)); g_assert_no_error (error);
    }
  }
  g_assert_true (fp_device_close_sync (device, NULL, &error)); g_assert_no_error (error);
  g_print ("PASS %s\n", scenario);
  return 0;
}
