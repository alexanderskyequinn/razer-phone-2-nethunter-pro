"""Package only candidate code, with no user or biometric data."""
from pathlib import Path
import hashlib
import io
import json
import tarfile

root = Path(__file__).resolve().parents[1]
base = root / 'build/kali/fingerprint'
files = {
    'libfprint-2.so.2': base/'libfprint-operations/libfprint-2.so.2',
    'aura-fpc-account-worker': base/'aura-fpc-bio',
    'aura-fprint-prompt': base/'aura-fprint-prompt',
    'fprint-device-inventory': base/'libfprint-operations/fprint-device-inventory',
}
for name in ('aura_fprint_bridge.py', 'aura_fprint_store.py', 'aura_fprint_worker.py'):
    files[name] = root/'port/aura-fingerprint'/name
hashes = {}
with tarfile.open(base/'libfprint-operations-candidate.tar', 'w') as tar:
    for name, path in files.items():
        data = path.read_bytes()
        if name.endswith('.py'): data = data.replace(b'\r\n', b'\n')
        hashes[name] = hashlib.sha256(data).hexdigest()
        info = tarfile.TarInfo(name)
        info.size = len(data)
        info.mode = 0o644 if name.endswith('.py') else 0o755
        tar.addfile(info, io.BytesIO(data))
    data = ''.join(f'{value}  {name}\n' for name, value in hashes.items()).encode()
    info = tarfile.TarInfo('SHA256SUMS'); info.size = len(data); info.mode = 0o644
    tar.addfile(info, io.BytesIO(data))
(base/'libfprint-operations-manifest.json').write_text(json.dumps(hashes, indent=2)+'\n')
print('Packaged candidate code and checksums')
