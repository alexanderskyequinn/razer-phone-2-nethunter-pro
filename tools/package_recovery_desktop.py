"""Package the bounded recovery launcher and its installed-image checksums."""
import hashlib
import io
import json
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / 'build/kali/rescue'
manifest = json.loads((out / 'manifest.json').read_text())
assert manifest['test_timeout_seconds'] == 0
for name in ('kali-rescue-install-slot-a.sh', 'kali-rescue-boot-test.sh'):
    path = root / 'diagnostic' / name
    text = path.read_text()
    import re
    text = re.sub(r'[a-f0-9]{64}(?=  /(?:dev/disk/by-partlabel/boot_a|var/lib/aura/aura-recovery-v1.img))', manifest['sha256'], text)
    path.write_text(text, newline='\n')
files = {
    'usr/local/bin/aura-recovery-app': 0o755,
    'usr/local/sbin/aura-enter-recovery': 0o755,
    'usr/share/applications/org.aura.Recovery.desktop': 0o644,
    'usr/share/polkit-1/actions/org.aura.recovery.policy': 0o644,
}
checks = (f"{manifest['sha256']}  /dev/disk/by-partlabel/boot_a\n"
          '2daeb1f36095b44b318410b3f4e8b5d989dcc7bb023d1426c492dab0a3053e74  /dev/disk/by-partlabel/dtbo_a\n'
          f"{manifest['qbootctl_sha256']}  /usr/local/libexec/aura-qbootctl\n")
with tarfile.open(out / 'recovery-desktop.tar.gz', 'w:gz') as archive:
    for name, mode in files.items():
        data = (root / 'port/kali-overlay' / name).read_bytes().replace(b'\r\n', b'\n')
        info = tarfile.TarInfo(name)
        info.size, info.mode = len(data), mode
        archive.addfile(info, io.BytesIO(data))
    info = tarfile.TarInfo('etc/aura-recovery.sha256')
    data = checks.encode()
    info.size, info.mode = len(data), 0o644
    archive.addfile(info, io.BytesIO(data))
print(hashlib.sha256((out / 'recovery-desktop.tar.gz').read_bytes()).hexdigest())
