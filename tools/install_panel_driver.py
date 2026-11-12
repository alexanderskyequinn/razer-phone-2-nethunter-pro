"""Install the local experimental panel into the pinned kernel build tree."""
from pathlib import Path
import sys
import shutil

root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]).resolve()
assert str(source) == '/var/tmp/aura-mainline-6.18.2/linux'
panel = source / 'drivers/gpu/drm/panel'
for name in ('panel-razer-nt36830.c', 'panel-razer-nt36830-commands.h'):
    shutil.copyfile(root / 'port' / name, panel / name)
entries = {
    'Kconfig': '\nconfig DRM_PANEL_RAZER_NT36830\n\ttristate "Experimental Razer Phone 2 NT36830 panel"\n\tdepends on OF && DRM_MIPI_DSI && BACKLIGHT_CLASS_DEVICE\n\thelp\n\t  Experimental dual DSI display support for Razer aura.\n',
    'Makefile': '\nobj-$(CONFIG_DRM_PANEL_RAZER_NT36830) += panel-razer-nt36830.o\n',
}
for name, entry in entries.items():
    path = panel / name
    data = path.read_text()
    if 'DRM_PANEL_RAZER_NT36830' not in data:
        path.write_text(data + entry)
