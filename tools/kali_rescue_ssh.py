"""USB-only SSH into the separate RAM recovery, with a distinct pinned host key."""
import argparse
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('script', type=Path)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--timeout', type=int, default=30)
p.add_argument('--session', default='v1', help='Unique identifier for this physically initiated RAM boot; pins its temporary host key separately')
a = p.parse_args()
import re
if not re.fullmatch(r'[A-Za-z0-9_-]{1,60}', a.session):
    p.error('session must be 1-60 letters, numbers, underscores or hyphens')
cmd = ['C:/Windows/System32/OpenSSH/ssh.exe', '-i', 'device-data/kali-access/id_ed25519',
       '-o','UserKnownHostsFile=device-data/kali-access/known_hosts_rescue_'+a.session,
       '-o','HostKeyAlias=aura-rescue-test-'+a.session,'-o','StrictHostKeyChecking=accept-new',
       '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','ConnectTimeout=5',
       '-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','root@192.0.2.1','sh -s']
payload = b'test -f /etc/aura-rescue-version || exit 90\n' + a.script.read_bytes().replace(b'\r\n',b'\n')
try:
    r = subprocess.run(cmd,input=payload,cwd=root,capture_output=True,timeout=a.timeout)
except subprocess.TimeoutExpired as e:
    r = subprocess.CompletedProcess(cmd,124,e.stdout or b'',(e.stderr or b'')+b'\nRecovery SSH timed out.\n')
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_bytes(r.stdout+r.stderr)
print(f'Saved recovery result (exit {r.returncode}) to {a.output}')
raise SystemExit(r.returncode)
