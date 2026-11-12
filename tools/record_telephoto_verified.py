import hashlib,json,shutil
from pathlib import Path
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1]
out=root/'build/kali'
archive=out/'camera/aura-libcamera-tele-trial.tar.gz'
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest=='e6f682ef503452519f8607832419e1722b9d552f8792fa089f390376644f8551'
for name in ['aura-libcamera-v5-telephoto.tar.gz','aura-libcamera.tar.gz']:shutil.copyfile(archive,out/'camera'/name)
p=json.loads((out/'camera/userspace-manifest.json').read_text())
p.update(archive_sha256=digest,status='v5: user verifies upright telephoto preview and saved photo in GNOME Camera. Main autofocus retained; telephoto autofocus pending.',rollback='/opt/aura-camera-before-telephoto')
p['telephoto_gain_model']='1024/(1024-code), sensor driver limits code to960'
p['evidence']+=['test-runs/snapshot/telecamera-persist-userspace.txt']
(out/'camera/userspace-manifest.json').write_text(json.dumps(p,indent=2)+'\n')
p=json.loads((out/'telecamera-progress.json').read_text())
p.update(updated_utc=datetime.now(timezone.utc).isoformat(),app_user_verified=True,userspace_persistent=True,status='User confirms upright telephoto live preview and saved photo. v5 camera libraries promoted persistently. Telephoto autofocus bring-up ongoing.')
p['limitations']=[x for x in p['limitations'] if x!='App preview/photo check pending']
p['evidence']+=['test-runs/snapshot/telecamera-persist-userspace.txt']
(out/'telecamera-progress.json').write_text(json.dumps(p,indent=2)+'\n')
