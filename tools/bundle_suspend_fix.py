"""Package the Razer Bluetooth suspend workaround independently of kernel images."""
import hashlib,io,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
overlay=root/'port/kali-overlay'
paths={'usr/local/sbin/aura-bluetooth-sleep':0o755,'etc/systemd/system/aura-bluetooth-sleep.service':0o644}
archive=root/'build/kali/suspend-fix.tar'
hashes={}
with tarfile.open(archive,'w') as tar:
 for name,mode in paths.items():
  data=(overlay/name).read_bytes().replace(b'\r\n',b'\n')
  info=tarfile.TarInfo(name);info.mode=mode;info.size=len(data);info.uname=info.gname='root'
  tar.addfile(info,io.BytesIO(data));hashes[name]=hashlib.sha256(data).hexdigest()
archive.with_suffix('.json').write_text(json.dumps({'files':hashes,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'purpose':'Power Bluetooth off across suspend while Razer IBS workaround is active; restore only if previously powered on. Bluetooth peripherals cannot wake phone. Idle-suspend preferences unchanged.','rollback':'Disable aura-bluetooth-sleep.service; if active, stop it first to restore the saved Bluetooth state. Remove only its unit and helper.'},indent=2)+'\n')
print(archive.with_suffix('.json').read_text())
