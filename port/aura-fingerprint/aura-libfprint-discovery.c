/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Discovery-only bring-up for the real platform resource device. No simulated
 * biometric result, enrollment, private template access or authentication.
 */
#include "drivers_api.h"

typedef struct _FpiDeviceAuraFpc { FpDevice parent; } FpiDeviceAuraFpc;
typedef struct _FpiDeviceAuraFpcClass { FpDeviceClass parent; } FpiDeviceAuraFpcClass;
GType fpi_device_aura_fpc_get_type (void);
G_DEFINE_TYPE (FpiDeviceAuraFpc, fpi_device_aura_fpc, FP_TYPE_DEVICE)

static const FpIdEntry ids[] = {
  { .udev_types = FPI_DEVICE_UDEV_SUBTYPE_PLATFORM,
    .platform_compatible = "razer,aura-fpc-resources",
    .platform_driver = "aura-fpc-resources" },
  { .udev_types = 0 }
};

static void probe (FpDevice *device)
{
  const char *path = fpi_device_get_udev_data (device, FPI_DEVICE_UDEV_SUBTYPE_PLATFORM);
  if (!path || !g_path_is_absolute (path)) {
    fpi_device_probe_complete (device, NULL, NULL,
                              fpi_device_error_new (FP_DEVICE_ERROR_NOT_SUPPORTED));
    return;
  }
  /* The secure firmware can match, but this discovery stage exposes no usable
   * biometric operation until account authorization and storage are connected. */
  fpi_device_update_features (device, FP_DEVICE_FEATURE_VERIFY, FP_DEVICE_FEATURE_NONE);
  fpi_device_probe_complete (device, "aura-fpc-qsee-v1",
                            "Razer Phone 2 fingerprint sensor (integration in progress)", NULL);
}

static void open_device (FpDevice *device)
{
  fpi_device_open_complete (device, fpi_device_error_new_msg (
    FP_DEVICE_ERROR_NOT_SUPPORTED,
    "Discovery is implemented; secure multi-user enrollment and verification are not yet connected"));
}

static void fpi_device_aura_fpc_init (FpiDeviceAuraFpc *self) { (void) self; }
static void fpi_device_aura_fpc_class_init (FpiDeviceAuraFpcClass *klass)
{
  FpDeviceClass *device = FP_DEVICE_CLASS (klass);
  device->id = "aura_fpc";
  device->full_name = "Razer Phone 2 Qualcomm TEE fingerprint sensor";
  device->type = FP_DEVICE_TYPE_UDEV;
  device->id_table = ids;
  device->scan_type = FP_SCAN_TYPE_PRESS;
  device->nr_enroll_stages = 0;
  device->probe = probe;
  device->open = open_device;
  device->features = FP_DEVICE_FEATURE_VERIFY;
}
