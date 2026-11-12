"""Generate a reviewable native platform discovery patch against pinned libfprint."""
from pathlib import Path
import argparse, difflib, shutil, subprocess
parser = argparse.ArgumentParser()
parser.add_argument('--operations', action='store_true')
args = parser.parse_args()
root=Path(__file__).resolve().parents[1]
source=root/'sources/libfprint-upstream'
tree=Path('/var/tmp/aura-libfprint-operations/source' if args.operations else '/var/tmp/aura-libfprint-platform/source')
assert subprocess.check_output(['git','-c',f'safe.directory={source}','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='6f9479c3d55f847c1b3769f28ceb99227f9858cf'
shutil.copytree(source,tree,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git'))
for script in tree.rglob('*.sh'):
    data=script.read_bytes()
    if b'\r\n' in data:script.write_bytes(data.replace(b'\r\n',b'\n'))
changes={}
def edit(name,old,new):
    p=tree/name
    text=p.read_text()
    assert text.count(old)==1,(name,old[:80],text.count(old))
    changes.setdefault(name,(source/name).read_text())
    p.write_text(text.replace(old,new))
edit('meson.build',"drivers_info = {", "drivers_info = {\n    'aura_fpc': { 'helper': ['udev'], 'optional': true },")
edit('libfprint/meson.build','driver_sources = {',"driver_sources = {\n    'aura_fpc': files('drivers/aura_fpc.c'),")
edit('libfprint/fpi-device.h','  FPI_DEVICE_UDEV_SUBTYPE_HIDRAW = 1 << 1,','  FPI_DEVICE_UDEV_SUBTYPE_HIDRAW = 1 << 1,\n  FPI_DEVICE_UDEV_SUBTYPE_PLATFORM = 1 << 2,')
edit('libfprint/fpi-device.h','      const gchar              *spi_acpi_id;','      const gchar              *spi_acpi_id;\n      const gchar              *platform_compatible;\n      const gchar              *platform_driver;')
edit('libfprint/fp-device-private.h','    gchar *hidraw_path;','    gchar *hidraw_path;\n    gchar *platform_path;')
edit('libfprint/fp-device.c','  PROP_FPI_UDEV_DATA_HIDRAW,','  PROP_FPI_UDEV_DATA_HIDRAW,\n  PROP_FPI_UDEV_DATA_PLATFORM,')
edit('libfprint/fp-device.c','  g_clear_pointer (&priv->udev_data.hidraw_path, g_free);','  g_clear_pointer (&priv->udev_data.hidraw_path, g_free);\n  g_clear_pointer (&priv->udev_data.platform_path, g_free);')
for block in ('get','set'):
    file=tree/'libfprint/fp-device.c';text=file.read_text()
    start=text.index('    case PROP_FPI_UDEV_DATA_HIDRAW:',text.index('fp_device_'+block+'_property'))
    end=text.index('      break;',start)+len('      break;')
    original=text[start:end]
    edit('libfprint/fp-device.c',original,original+'\n\n'+original.replace('HIDRAW','PLATFORM').replace('hidraw_path','platform_path'))
edit('libfprint/fp-device.c','  properties[PROP_FPI_DRIVER_DATA] =', '''  properties[PROP_FPI_UDEV_DATA_PLATFORM] =
    g_param_spec_string ("fpi-udev-data-platform", "Udev data: platform sysfs path",
                         "Private: Platform resource device path", NULL,
                         G_PARAM_STATIC_STRINGS | G_PARAM_READWRITE | G_PARAM_CONSTRUCT_ONLY);

  properties[PROP_FPI_DRIVER_DATA] =''')
edit('libfprint/fpi-device.c','    case FPI_DEVICE_UDEV_SUBTYPE_HIDRAW:\n      return priv->udev_data.hidraw_path;', '    case FPI_DEVICE_UDEV_SUBTYPE_PLATFORM:\n      return priv->udev_data.platform_path;\n\n    case FPI_DEVICE_UDEV_SUBTYPE_HIDRAW:\n      return priv->udev_data.hidraw_path;')
edit('libfprint/fp-context.c','    g_autoptr(GList) hidraw_devices = g_udev_client_query_by_subsystem (udev_client, "hidraw");','    g_autoptr(GList) hidraw_devices = g_udev_client_query_by_subsystem (udev_client, "hidraw");\n    g_autoptr(GList) platform_devices = g_udev_client_query_by_subsystem (udev_client, "platform");')
edit('libfprint/fp-context.c','            GList *matched_spidev = NULL, *matched_hidraw = NULL;','            GList *matched_spidev = NULL, *matched_hidraw = NULL, *matched_platform = NULL;')
edit('libfprint/fp-context.c','            if (entry->udev_types & FPI_DEVICE_UDEV_SUBTYPE_SPIDEV)', '''            if (entry->udev_types & FPI_DEVICE_UDEV_SUBTYPE_PLATFORM)
              {
                /* Require an exact DT compatible and the expected bound driver.
                 * A similarly named node or unrelated TEE device is insufficient. */
                if (!entry->platform_compatible || !entry->platform_driver)
                  continue;
                for (matched_platform = platform_devices; matched_platform; matched_platform = matched_platform->next)
                  {
                    GUdevDevice *candidate = matched_platform->data;
                    gint count = g_udev_device_get_property_as_int (candidate, "OF_COMPATIBLE_N");
                    gboolean matches = FALSE;
                    if (count <= 0 || count > 64 ||
                        g_strcmp0 (g_udev_device_get_driver (candidate), entry->platform_driver))
                      continue;
                    for (gint n = 0; n < count; n++)
                      {
                        g_autofree gchar *key = g_strdup_printf ("OF_COMPATIBLE_%d", n);
                        if (!g_strcmp0 (g_udev_device_get_property (candidate, key), entry->platform_compatible))
                          { matches = TRUE; break; }
                      }
                    if (matches && g_udev_device_get_sysfs_path (candidate))
                      break;
                  }
                if (!matched_platform)
                  continue;
              }
            if (entry->udev_types & FPI_DEVICE_UDEV_SUBTYPE_SPIDEV)''')
edit('libfprint/fp-context.c','                                        "fpi-udev-data-hidraw", (matched_hidraw ? g_udev_device_get_device_file (matched_hidraw->data) : NULL),','                                        "fpi-udev-data-hidraw", (matched_hidraw ? g_udev_device_get_device_file (matched_hidraw->data) : NULL),\n                                        "fpi-udev-data-platform", (matched_platform ? g_udev_device_get_sysfs_path (matched_platform->data) : NULL),')
edit('libfprint/fp-context.c','            /* remove entries from list to avoid conflicts */','''            /* remove entries from list to avoid conflicts */
            if (matched_platform)
              {
                g_object_unref (matched_platform->data);
                platform_devices = g_list_delete_link (platform_devices, matched_platform);
              }''')
edit('libfprint/fp-context.c','    g_list_foreach (hidraw_devices, (GFunc) g_object_unref, NULL);','    g_list_foreach (hidraw_devices, (GFunc) g_object_unref, NULL);\n    g_list_foreach (platform_devices, (GFunc) g_object_unref, NULL);')
edit('libfprint/fprint-list-metainfo.c','      if (cls->type != FP_DEVICE_TYPE_USB)\n        continue;', '''      if (cls->type == FP_DEVICE_TYPE_UDEV)
        {
          for (const FpIdEntry *entry = cls->id_table; entry->udev_types; entry++)
            if ((entry->udev_types & FPI_DEVICE_UDEV_SUBTYPE_PLATFORM) && entry->platform_compatible)
              {
                g_autofree gchar *compatible = g_markup_escape_text (entry->platform_compatible, -1);
                g_string_append_printf (provided_modules, "    <modalias>of:N*T*C%s*</modalias>\\n", compatible);
              }
        }
      if (cls->type != FP_DEVICE_TYPE_USB)
        continue;''')
name='libfprint/drivers/aura_fpc.c';changes[name]=''
shutil.copyfile(root/('port/aura-fingerprint/aura-libfprint-operations.c' if args.operations else 'port/aura-fingerprint/aura-libfprint-discovery.c'),tree/name)
patch=''.join(''.join(difflib.unified_diff(before.splitlines(True),(tree/name).read_text().splitlines(True),fromfile='a/'+name,tofile='b/'+name)) for name,before in changes.items())
(root/('port/libfprint-aura-operations.patch' if args.operations else 'port/libfprint-aura-platform.patch')).write_text(patch)
print(tree)
