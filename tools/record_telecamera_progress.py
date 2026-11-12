import json
from pathlib import Path
from datetime import datetime, timezone
root = Path(__file__).resolve().parents[1]
out = root/'build/kali'
p = json.loads((out/'camera-probe-progress.json').read_text())
p.update(version='v22', installed=True, status='Both probe bugs corrected. Clean v22 boot verified; telephoto IMX351 identity 0x0351 read successfully. Front address0x2d returned -6 (no acknowledgement). Probe unloaded without kernel fault and all supplies released.', boot=json.loads((out/'boot-manifest-v22.json').read_text())['files']['aura-kali-trial-v22.img'])
p['recovery'] = 'User reset cleared the earlier fault. Successful SSH and verified v22 boot followed.'
p['evidence'] += ['test-runs/snapshot/camera-busfix-verify.txt','test-runs/snapshot/camera-identify-v22.txt','test-runs/snapshot/camera-probe-cleanup-v22.txt']
p['next'] = ['Verify v23 telephoto capture candidate', 'Capture and inspect telephoto frames', 'Continue front camera power-sequence diagnostics']
(out/'camera-probe-progress.json').write_text(json.dumps(p, indent=2)+'\n')
data = dict(updated_utc=datetime.now(timezone.utc).isoformat(), status='v23 update launched; not yet boot/capture verified', boot=json.loads((out/'boot-manifest-v23.json').read_text())['files']['aura-kali-trial-v23.img'], module='build/kali/telecamera/imx351.ko', sensor_identity_verified=True, capture_verified=False, limitations=['Single retained4208x3120RAW10mode','No telephoto autofocus yet','libcamera sensor helper not yet added','Front sensor does not acknowledge; cause not established'])
(out/'telecamera-progress.json').write_text(json.dumps(data,indent=2)+'\n')
