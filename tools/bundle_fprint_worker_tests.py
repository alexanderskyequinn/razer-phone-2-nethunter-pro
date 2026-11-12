"""Package isolated synthetic checks; never bundle private device state."""
from pathlib import Path
import hashlib
import re
import tarfile

root = Path(__file__).resolve().parents[1]
files = ['port/aura-fingerprint/aura_fprint_store.py', 'port/aura-fingerprint/aura_fprint_worker.py',
         'tests/test_fprint_worker.py', 'diagnostic/aura-standard-prompt-test.py',
         'diagnostic/aura-fprint-account-trial.py', 'build/kali/fingerprint/aura-fpc-bio']
out = root / 'build/kali/fingerprint/account-worker-test.tar'
with tarfile.open(out, 'w') as archive:
    for name in files:
        info = archive.gettarinfo(root/name, arcname=name)
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        info.mode = 0o700 if name.endswith('/aura-fpc-bio') else 0o644
        with (root/name).open('rb') as stream:
            archive.addfile(info, stream)
digest = hashlib.sha256(out.read_bytes()).hexdigest()
installer = root / 'diagnostic/kali-fprint-worker-tests.sh'
text, count = re.subn(r'[0-9a-f]{64}  /var/tmp/aura-account-worker-test.tar', digest + '  /var/tmp/aura-account-worker-test.tar', installer.read_text(encoding='utf-8'))
assert count == 1
installer.write_text(text, encoding='utf-8', newline='\n')
print(digest)
