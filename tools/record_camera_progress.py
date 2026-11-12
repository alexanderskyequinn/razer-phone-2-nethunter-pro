"""Record camera evidence without conflating first image capture with a finished camera port."""
import hashlib
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'build/kali/camera-progress.json'
data=json.loads(p.read_text())
health=(root/'test-runs/kali-trial-v18/first-boot.txt').read_text()
scene=(root/'test-runs/kali-trial-v18/scene-test.txt').read_text()
assert 'imx363 16-0010' in health and '0 loaded units listed.' in health
assert '15240960 /var/lib/aura/camera-tests/scene.raw' in scene
data.update(installed=True, boot_id='b4cc9e42-0a88-4318-9989-84ef8bc89874', module_sha256=hashlib.sha256((root/'build/kali/camera/imx363.ko').read_bytes()).hexdigest())
processed=(root/'test-runs/kali-trial-v18/processed-test.txt').read_text()
preview=(root/'test-runs/kali-trial-v18/preview-status.txt').read_text()
assert 'processed_capture_exit=0' in processed
assert '30.27 fps' in preview and 'suspended' in preview
finish=(root/'test-runs/kali-trial-v18/camera-finish.txt').read_text()
assert 'suspended' in finish and '0 loaded units listed.' in finish
data['status']='v18 booted; main rear IMX363 identifies and powers down when idle. Full 4032x3024 RAW10 scene captured and visually verified. Incomplete inherited 1080p mode removed. Private libcamera IMX363 helper, portrait presentation, central-input metering and smoothed white balance installed. User confirms live upright image, responding brightness and smoother color transitions. Preview sustains about 30 fps; camera suspends on exit, no failed system services.'
data['limitations']='Preview milestone, not a finished camera app: autofocus, OIS, telephoto and calibrated colors/exposure timing pending. Preview has no shutter/save interface. Orientation correction is in presentation only; raw files remain in sensor orientation. Sensor-generated color bars are blank and PN9 partial, while normal full-frame scene capture and receiver pattern pass. Front camera was already inoperable under Android.'
data['user_validation']={'live_image':True,'orientation':'Upright after SDL counterclockwise correction','exposure':'User confirms brightness adjusts after cover/uncover and after metering update.','white_balance':'User confirms smoother color changes after temporal filtering.'}
data['evidence']=['test-runs/kali-trial-v18/'+s for s in ['first-boot.txt','scene-test.txt','scene.json','receiver-pattern-second.txt','module-update.txt','libcamera-full-mode-test.txt','userspace-install.txt','processed-test.txt','preview-status.txt','camera-final-health.txt']]
userspace_path=root/'build/kali/camera/userspace-manifest.json'
userspace=json.loads(userspace_path.read_text())
userspace['status']='v2 installed in /opt/aura-camera; user confirms upright preview, adjusting exposure and smoother white balance. About 30 fps verified; idle suspend and system health pass.'
userspace['rollback']='/opt/aura-camera-before-white-balance'
userspace['evidence']=['test-runs/kali-trial-v18/'+s for s in ['userspace-install.txt','processed-test.txt','preview-status.txt']]
userspace['evidence'] += ['test-runs/kali-trial-v18/'+s for s in ['portrait-install-wifi.txt','userspace-v2-install.txt','camera-finish.txt']]
data['evidence'] += userspace['evidence'][3:]
userspace_path.write_text(json.dumps(userspace,indent=2)+'\n')
data['userspace']=userspace
p.write_text(json.dumps(data,indent=2)+'\n')
p=root/'build/kali/boot-manifest-v18.json'
manifest=json.loads(p.read_text())
manifest.update(status=data['status'],rollback=data['rollback'],evidence=data['evidence'])
for dest in [p,root/'build/kali/boot-manifest.json']:
    dest.write_text(json.dumps(manifest,indent=2)+'\n')
print(data['status'])
