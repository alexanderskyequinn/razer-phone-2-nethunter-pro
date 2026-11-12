"""Preserve the NFC module tested across repeated controller power cycles."""
import hashlib
import json
import tarfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]
module = root / 'build/kali/nfc-cold-irq/nxp-nci_i2c.ko.zst'
digest = hashlib.sha256(module.read_bytes()).hexdigest()
assert digest == '45c60017a472b33a0f124dc1324601bb817cb5dbd1b13ab22f5e460b066efd1d'
name = 'lib/modules/6.18.2-aura-bringup1+/kernel/drivers/nfc/nxp-nci/nxp-nci_i2c.ko.zst'
output = root / 'build/kali/nfc-restart-fix.tar'
with tarfile.open(output, 'w') as archive:
    info = archive.gettarinfo(str(module), arcname=name)
    info.uid = info.gid = 0
    info.uname = info.gname = 'root'
    info.mode = 0o644
    with module.open('rb') as stream:
        archive.addfile(info, stream)
output.with_suffix('.json').write_text(json.dumps({
    'kernel_revision': 'a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0',
    'boot_image': 'aura-kali-trial-v11.img',
    'patch': 'port/nxp-nci-cold-irq.patch',
    'build': 'tools/build_nfc_cold_irq.sh',
    'module_sha256': digest,
    'archive_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    'verification': 'Three consecutive controller start/stop cycles pass after clean boot. Ninety-second polling window completes and powers down. Tested payment card not detected; RF/card cross-check unresolved.',
    'evidence': 'test-runs/kali-trial-v11/nfc-three-cycles.txt; test-runs/kali-trial-v11/nfc-tag-result-fixed.txt',
    'limitations': 'Avoid live driver reload until DT interrupt trigger matches driver rising-edge request; original v11 DT is level-high. Prior reload caused an IRQ mapping failure and kernel oops. Cleanup fix is included but failure path has not been retested.',
    'rollback_module_on_phone': '/var/lib/aura/nxp-nci_i2c-v11-original.ko.zst',
}, indent=2) + '\n')
