"""Build the v20 panel timing candidate and a guarded v19 rollback installer."""
from pathlib import Path
import gzip
import json
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
out = root / 'build/kali'
pack = root / 'tools/pack_kali_boot.py'
text = pack.read_text()
if "'v20'" not in text:
    pack.write_bytes(text.replace("'v19'", "'v19', 'v20'").encode())
subprocess.run([sys.executable, str(pack), '--version', 'v20', '--kernel-dir', str(out / 'panel-wake-kernel')], check=True)
manifest = json.loads((out / 'boot-manifest-v20.json').read_text())
old = '985deb8f7761969b558cfdbb1025cc363173dedfe57bb24d7844919b984dc951'
new = manifest['files']['aura-kali-trial-v20.img']['sha256']
installer = (root / 'diagnostic/kali-install-boot-v19.sh').read_text()
installer = installer.replace('old=f7824f9506b100ab17a9a72b1a3e0e78bfd9b0a01650c87b2b5e9d461ae68580', 'old='+old).replace('new='+old, 'new='+new)
installer = installer.replace('aura-kali-trial-v19.img', 'aura-kali-trial-v20.img').replace('boot-v18-before-focus.img', 'boot-v19-before-panel-wake.img').replace('focus-before-reboot', 'panel-wake-before-reboot').replace('v19 boot image', 'v20 boot image').replace('v18 backup', 'v19 backup')
assert 'old='+old in installer and 'new='+new in installer
(root / 'diagnostic/kali-install-boot-v20.sh').write_bytes(installer.encode())
launch = f'''set -eu
test "$(cat /etc/aura-install-id)" = 'REPLACE_WITH_YOUR_INSTALL_ID'
gzip -t /var/lib/aura/aura-kali-trial-v20.img.gz
gzip -dc /var/lib/aura/aura-kali-trial-v20.img.gz > /var/lib/aura/aura-kali-trial-v20.img
echo '{new}  /var/lib/aura/aura-kali-trial-v20.img' | sha256sum -c -
sh -n /var/lib/aura/kali-install-boot-v20.sh
systemd-run --unit=aura-panel-wake-update --property=StandardOutput=append:/var/lib/aura/panel-wake-update.log --property=StandardError=append:/var/lib/aura/panel-wake-update.log /bin/sh /var/lib/aura/kali-install-boot-v20.sh
'''
(root / 'diagnostic/kali-panel-wake-update-launch.sh').write_bytes(launch.encode())
with gzip.GzipFile(out / 'aura-kali-trial-v20.img.gz', 'wb', mtime=0) as f:
    f.write((out / 'aura-kali-trial-v20.img').read_bytes())
print(new)
