/* SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <libfprint/fprint.h>
int main (void)
{
  g_autoptr(FpContext) context = fp_context_new ();
  GPtrArray *devices = fp_context_get_devices (context);
  printf ("DEVICE_COUNT=%u\n", devices->len);
  for (guint i = 0; i < devices->len; i++) {
    FpDevice *device = g_ptr_array_index (devices, i);
    printf ("DRIVER=%s ID=%s FEATURES=%u\n", fp_device_get_driver (device),
            fp_device_get_device_id (device), fp_device_get_features (device));
    g_autoptr(GError) error = NULL;
    if (fp_device_open_sync (device, NULL, &error)) {
      fprintf (stderr, "Discovery-only driver unexpectedly permitted opening\n");
      return 1;
    }
    if (!g_error_matches (error, FP_DEVICE_ERROR, FP_DEVICE_ERROR_NOT_SUPPORTED)) return 2;
    puts ("OPEN_REFUSED_AS_EXPECTED");
  }
  return 0;
}
