import hashlib, json, shutil
from pathlib import Path
from datetime import datetime, timezone
root=Path(__file__).resolve().parents[1]
base=root/'build/kali/camera'
candidate=base/'aura-libcamera-af-trial.tar.gz'
sha=hashlib.sha256(candidate.read_bytes()).hexdigest()
assert sha=='3f56ebda35e54fbddea2efd09fd3b85f70026314f3cde62cc016f5f973b2d513'
shutil.copyfile(candidate,base/'aura-libcamera-v4-autofocus.tar.gz')
shutil.copyfile(candidate,base/'aura-libcamera.tar.gz')
p=base/'userspace-manifest.json'
d=json.loads(p.read_text())
d.update(archive_sha256=sha,status='v4 autofocus installed persistently. User confirms near/far image looks good. Bounded contrast search scoped to IMX363/BU64753, stock50..800 range, smoothed edge-energy metric. Manual lens-position/diopter calibration not exposed.',rollback='/opt/aura-camera-before-autofocus')
d['evidence'] += ['test-runs/snapshot/focus-readback.txt','test-runs/snapshot/autofocus-trial-status.txt','test-runs/snapshot/autofocus-persist2.txt']
p.write_text(json.dumps(d,indent=2)+'\n')
af={'updated_utc':datetime.now(timezone.utc).isoformat(),'installed':True,'user_verified':True,'status':d['status'],'archive_sha256':sha,'evidence':d['evidence'][-3:],'limits':['Contrast autofocus prototype; no phase-detect support','Focus can take several seconds and still needs low-light/moving-subject characterization','OIS, telephoto and front sensor bring-up and video testing remain']}
(root/'build/kali/autofocus-progress.json').write_text(json.dumps(af,indent=2)+'\n')
p=root/'build/kali/camera-progress.json'; c=json.loads(p.read_text());c['autofocus']=af;c['userspace']=d;p.write_text(json.dumps(c,indent=2)+'\n')
p=root/'port-status.json';s=json.loads(p.read_text(encoding='utf-8'));s['current_followup']['autofocus']=af;s['hardware_progress']['verified']['rear_camera_autofocus']=af['status'];p.write_text(json.dumps(s,indent=2)+'\n',encoding='utf-8')
print('Autofocus canonical archive and progress updated.')
