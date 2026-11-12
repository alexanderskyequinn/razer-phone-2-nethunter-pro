"""Copy the bounded signed vendor program only, never secure user storage."""
import hashlib
from pathlib import Path
import subprocess
from kali_ssh import SSH, ROOT

result = subprocess.run(SSH + ['root@192.0.2.78',
    'head -c 232947 /dev/disk/by-partlabel/keymaster_b'],
    cwd=ROOT, capture_output=True, timeout=20, check=True)
program = result.stdout
assert len(program) == 232947 and program[:6] == b'\x7fELF\x02\x01'
target = ROOT / 'build/kali/fingerprint/keymaster64.elf'
target.write_bytes(program)
print('Copied signed program:',len(program),'bytes; SHA256',hashlib.sha256(program).hexdigest())
