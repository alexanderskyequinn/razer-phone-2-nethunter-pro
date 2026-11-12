"""Package the matching NFC modules and configuration used for validation."""
import hashlib
import json
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
module_base = 'lib/modules/6.18.2-aura-bringup1+/kernel/'
files = [
    ('build/kali/nci-parser-fix/nci.ko.zst', module_base+'net/nfc/nci/nci.ko.zst', '8428205815223513e4b2854ce10a3850c7b13d85038585d1aa92ea243fafb31b'),
    ('build/kali/nfc-screen-state/nxp-nci.ko.zst', module_base+'drivers/nfc/nxp-nci/nxp-nci.ko.zst', '54ea3d0530b5907622c56ad2f83d1e9c1668b1009c27523c0cdbb43b2987efd1'),
    ('build/kali/nfc-cold-irq/nxp-nci_i2c.ko.zst', module_base+'drivers/nfc/nxp-nci/nxp-nci_i2c.ko.zst', '45c60017a472b33a0f124dc1324601bb817cb5dbd1b13ab22f5e460b066efd1d'),
    ('build/kali/nfc-screen-state/razer-aura-nci-config.bin', 'lib/firmware/nxp/razer-aura-nci-config.bin', 'be86e86d8266225ef80f98b3e2b0c370b5d6f7b84535e4ab9d9c97f3375283cf'),
]
for source, destination, digest in files:
    assert hashlib.sha256((root/source).read_bytes()).hexdigest() == digest, source
output = root/'build/kali/nfc-complete-fix.tar'
with tarfile.open(output, 'w') as archive:
    for source, destination, digest in files:
        path = root/source
        info = archive.gettarinfo(str(path), arcname=destination)
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        info.mode = 0o644
        with path.open('rb') as stream:
            archive.addfile(info, stream)
manifest = {
    'kernel_revision': 'a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0',
    'upstream_parser_fix': '571dcbeb8e635182bb825ae758399831805693c2',
    'source': 'https://github.com/torvalds/linux/commit/571dcbeb8e635182bb825ae758399831805693c2',
    'files': [{'path': destination, 'sha256': digest} for _, destination, digest in files],
    'archive_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    'verification': 'Installed and booted. Three initialization/power-down cycles pass. Known-working ISO14443 card detected by Linux (protocol mask 0x10) and controller powered down cleanly. No card contents read; data exchange, other protocols and emulation not yet validated.',
    'evidence': ['test-runs/kali-trial-v11/nci-parser-card-result.txt', 'test-runs/kali-trial-v11/nci-parser-three-cycles.txt', 'test-runs/kali-trial-v11/nfc-final-health.txt'],
    'rollback': ['/var/lib/aura/nci-v11-original.ko.zst', '/var/lib/aura/nxp-nci-v11-original.ko.zst', '/var/lib/aura/nxp-nci_i2c-v11-original.ko.zst'],
    'installation': 'Use only matching aura kernel. Run depmod and reboot after installation; do not hot-reload NFC modules.',
    'excluded_candidate': 'nfc-tag-detector configuration was prepared but not installed; parser evidence superseded this experiment.',
}
output.with_suffix('.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(output)
