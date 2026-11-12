"""Archive the experimental Razer NFC setup with explicit validation status."""
import hashlib
import json
import tarfile
import argparse
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--screen-state', action='store_true')
args = parser.parse_args()
output = root / 'build/kali/nfc-board-config-fix.tar'
base = 'lib/modules/6.18.2-aura-bringup1+/kernel/drivers/nfc/nxp-nci/'
files = [
    ('build/kali/nfc-board-config/nxp-nci.ko.zst', base + 'nxp-nci.ko.zst', '77dfd9252cdf95c4365d93204af730df7f600a259a85ec6b4cacd19b242abee2'),
    ('build/kali/nfc-cold-irq/nxp-nci_i2c.ko.zst', base + 'nxp-nci_i2c.ko.zst', '45c60017a472b33a0f124dc1324601bb817cb5dbd1b13ab22f5e460b066efd1d'),
    ('build/kali/nfc-board-config/razer-aura-nci-config.bin', 'lib/firmware/nxp/razer-aura-nci-config.bin', '9dce61b905f04009ba82bf6579570f45f229e9a66b4a678aa84cf3191c03f466'),
]
if args.screen_state:
    output = root / 'build/kali/nfc-screen-state-fix.tar'
    files[0] = ('build/kali/nfc-screen-state/nxp-nci.ko.zst', files[0][1], '54ea3d0530b5907622c56ad2f83d1e9c1668b1009c27523c0cdbb43b2987efd1')
    files[2] = ('build/kali/nfc-screen-state/razer-aura-nci-config.bin', files[2][1], 'be86e86d8266225ef80f98b3e2b0c370b5d6f7b84535e4ab9d9c97f3375283cf')
for source, destination, digest in files:
    assert hashlib.sha256((root / source).read_bytes()).hexdigest() == digest, source
with tarfile.open(output, 'w') as archive:
    for source, destination, digest in files:
        path = root / source
        info = archive.gettarinfo(str(path), arcname=destination)
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        info.mode = 0o644
        with path.open('rb') as stream:
            archive.addfile(info, stream)
manifest = {
    'kernel_revision': 'a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0',
    'files': [{'path': dest, 'sha256': digest} for _, dest, digest in files],
    'archive_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    'verification': 'Installed and booted. All 12 original-board configuration commands acknowledged successfully; three consecutive controller start/stop cycles pass. Other phone in emulation mode still not detected. Superseded on phone by experimental screen-state module; this archive preserves the prior tested initialization.',
    'evidence': ['test-runs/kali-trial-v11/nfc-board-first-check.txt', 'test-runs/kali-trial-v11/nfc-board-three-cycles.txt'],
    'patches': ['port/nxp-nci-cold-irq.patch', 'port/nxp-nci-aura-config.patch'],
    'configuration_manifest': 'build/kali/nfc-board-config/manifest.json',
    'installation': 'Install only on the matching aura kernel, run depmod, then reboot. Do not hot-reload NFC modules.',
    'rollback_core_on_phone': '/var/lib/aura/nxp-nci-v11-original.ko.zst',
    'rollback_i2c_on_phone': '/var/lib/aura/nxp-nci_i2c-v11-original.ko.zst',
}
if args.screen_state:
    manifest.update({
        'verification': 'Installed and booted. Original-board configuration and screen-on command accepted, polling starts and stops. Physical emulation test pending.',
        'evidence': ['test-runs/kali-trial-v11/nfc-screen-state-first-check.txt'],
        'configuration_manifest': 'build/kali/nfc-screen-state/manifest.json',
        'rollback_core_on_phone': '/var/lib/aura/nxp-nci-board-config.ko.zst',
        'rollback_configuration_on_phone': '/var/lib/aura/nfc-board-config.bin',
    })
output.with_suffix('.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(output)
