from pathlib import Path
import hashlib
import json
import tarfile
import uuid
root=Path(__file__).resolve().parents[1]
destination=Path('/var/tmp/aura-kali-rootfs')
data=json.loads((root/'build/kali/wifi-access.json').read_text())
assert data['installed'] and (destination/'etc/aura-install-id').read_text().strip()==data['install_id']
archive=root/'build/kali/wifi-access.tar'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==data['archive_sha256']
with tarfile.open(archive) as package:
    package.extractall(destination,filter='data')
profile=destination/'etc/aura-wifi-ssh-profile'
profile.write_text(str(uuid.UUID(data['profile_uuid']))+'\n')
profile.chmod(0o600)
link=destination/'etc/systemd/system/multi-user.target.wants/aura-wifi-ssh.service'
link.parent.mkdir(exist_ok=True,parents=True)
if not link.is_symlink():
    link.symlink_to('/etc/systemd/system/aura-wifi-ssh.service')
print('Approved Wi-Fi profile and reconnect service staged for this phone.')
