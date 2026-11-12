"""Resume the exact audited software export across intermittent USB disconnects."""
import subprocess
from pathlib import Path
from kali_ssh import SSH, ROOT
args=['C:/Windows/System32/OpenSSH/sftp.exe', *SSH[1:], '-o','ServerAliveInterval=5',
      '-o','ServerAliveCountMax=2','-b','-','root@192.0.2.1']
batch='get -a /var/tmp/aura-release-runtime.tar.gz build/kali/release/aura-release-runtime.tar.gz\nget /var/tmp/aura-release-runtime-manifest.json build/kali/release/aura-release-runtime-manifest.json\n'
try:
    r=subprocess.run(args,input=batch.encode(),capture_output=True,cwd=ROOT,timeout=90)
    print((r.stdout+r.stderr).decode(errors='replace'))
    raise SystemExit(r.returncode)
except subprocess.TimeoutExpired:
    print('Transfer timed out; rerun to resume the same export.')
    raise SystemExit(124)
