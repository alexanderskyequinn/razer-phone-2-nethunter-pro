from pathlib import Path
import hashlib
import json
import re
import tarfile

root = Path(__file__).resolve().parents[1]
files = {
    'usr/local/bin/aura-fingerprint-app': 'port/aura-fingerprint/aura-fingerprint-app',
    'usr/local/libexec/aura-fingerprint-helper': 'port/aura-fingerprint/aura-fingerprint-helper',
    'usr/local/libexec/aura-fpc-bio': 'build/kali/fingerprint/aura-fpc-bio',
    'usr/local/libexec/aura-qsee-rpmb-authenticated': 'build/kali/fingerprint-listener/aura-qsee-rpmb-authenticated',
    'usr/share/applications/org.aura.Fingerprint.desktop': 'port/aura-fingerprint/org.aura.Fingerprint.desktop',
    'usr/share/icons/hicolor/scalable/apps/org.aura.Fingerprint.svg': 'port/aura-fingerprint/org.aura.Fingerprint.svg',
    'usr/share/polkit-1/actions/org.aura.fingerprint.policy': 'port/aura-fingerprint/org.aura.fingerprint.policy',
    'etc/systemd/system/aura-fingerprint-storage.service': 'port/aura-fingerprint/aura-fingerprint-storage.service',
}
bundle = root / 'build/kali/fingerprint-app.tar'
hashes = {}
with tarfile.open(bundle, 'w') as archive:
    for name, source in files.items():
        path = root / source
        info = archive.gettarinfo(path, arcname=name)
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        info.mode = 0o755 if name.startswith(('usr/local/bin/', 'usr/local/libexec/')) else 0o644
        with path.open('rb') as stream:
            archive.addfile(info, stream)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
(root / 'build/kali/fingerprint-app-manifest.json').write_text(json.dumps({'sha256': digest, 'files': hashes}, indent=2) + '\n')
installer = root / 'diagnostic/kali-fingerprint-app-install.sh'
script = installer.read_text()
script, changes = re.subn(r"[a-f0-9]{64}  /var/lib/aura/fingerprint-app.tar", digest + '  /var/lib/aura/fingerprint-app.tar', script)
assert changes == 1
installer.write_text(script, newline='\n')
print(digest)
