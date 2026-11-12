from pathlib import Path
import hashlib
import json
import tarfile
root=Path(__file__).resolve().parents[1]
archive=root/'build/kali/camera/aura-libcamera.tar.gz'
with tarfile.open(archive) as package:
    for m in package.getmembers():
        assert not m.name.startswith('/') and '..' not in Path(m.name).parts
        assert m.name=='opt' or m.name.startswith('opt/aura-camera/') or m.name=='opt/aura-camera'
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
script=f'''set -eu
test "$(cat /etc/aura-install-id)" = 'REPLACE_WITH_YOUR_INSTALL_ID'
echo '{digest}  /var/lib/aura/aura-libcamera.tar.gz' | sha256sum -c -
test ! -e /opt/aura-camera
tar -xzf /var/lib/aura/aura-libcamera.tar.gz -C /
install -m 0755 /var/lib/aura/aura-camera-preview /usr/local/bin/aura-camera-preview
install -m 0644 /var/lib/aura/aura-camera-preview.desktop /usr/share/applications/aura-camera-preview.desktop
LD_LIBRARY_PATH=/opt/aura-camera/lib ldd /opt/aura-camera/bin/cam
LD_LIBRARY_PATH=/opt/aura-camera/lib /opt/aura-camera/bin/cam -l
'''
(root/'diagnostic/kali-camera-userspace-install.sh').write_bytes(script.encode())
(root/'build/kali/camera/userspace-manifest.json').write_text(json.dumps({'archive_sha256':digest,'source_sha256':hashlib.sha256((root/'sources/libcamera_0.7.2.orig.tar.gz').read_bytes()).hexdigest(),'prefix':'/opt/aura-camera','gain_model':'512/(512-code), stock Razer binary conversion verified at 0xbe8/0xc60; code cap480','status':'Built, not yet installed'},indent=2)+'\n')
print(digest)
