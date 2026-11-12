import json
from pathlib import Path
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1]
out=root/'build/kali'
data={
 'updated_utc':datetime.now(timezone.utc).isoformat(),
 'boot_version':'v25',
 'boot_sha256':'571e3302fd053920dc178c495a6267addd9f5827ed132b37d09b6f51ef37d502',
 'kernel':'6.18.2-aura-bringup1+ #13',
 'module':'lc898217xc',
 'module_sha256':'268587665456a82baded5f7dd8e9402ad66c6f0793a9e83aad3464eea4cc8bee',
 'kernel_driver_persistent':True,
 'status':'Telephoto focus identity0x72, servo status0x00, and bounded60/300/610/60 register readback verified. Diagnostic images visibly sharpen at610 vs60. Both rear cameras advertise AF with isolated userspace trial. User near/far and main-camera regression checks pending.',
 'native_driver_correction':'v24 matched existing lc898217xc driver but had incorrect supply names. v25 uses vdd/vana and Razer-specific stock initialization plus60..610control bounds in existing driver. Earlier standalone lc898217 prototype is superseded and not installed.',
 'optical_limit':'Exposure changed during sweep, so numerical focus curve is not a controlled comparison. Saved frames provide qualitative optical evidence.',
 'trial_prefix':'/opt/aura-camera-telefocus-test',
 'trial_sha256':'d655cf613482f5dd77b6eb3c4041809f1b9697f6227c9ee7c3b2902fecbd4680',
 'trial_persistent':False,
 'pending_user_question':'Does telephoto focus sharpen/settle on near/far targets, and does main autofocus still work?',
 'persist_script_ready':'diagnostic/kali-telefocus-persist-userspace.sh',
 'rollback_boot':'/var/lib/aura/boot-v23-before-telefocus.img',
 'evidence':['test-runs/snapshot/native-telefocus-check.txt','test-runs/snapshot/telefocus-optical.txt','test-runs/snapshot/aura-telefocus-60.png','test-runs/snapshot/aura-telefocus-610.png','test-runs/snapshot/telefocus-health.txt'],
 'check_note':'native-telefocus-check initially exited1 due to unrelated longstanding display/GPU dummy-supply messages; narrowed check and subsequent health check found no lens/kernel faults.',
 'remaining':['Validate and persist telephoto autofocus','OIS and video testing','Front sensor unresponsive in two bounded probes; physical supply/module health unresolved','Fingerprint after camera work; read-only interface inventory saved']}
(out/'telefocus-progress.json').write_text(json.dumps(data,indent=2)+'\n')
p=json.loads((out/'camera-completion-progress.json').read_text())
p.update(updated_utc=data['updated_utc'],status=data['status'])
p['remaining']=data['remaining']
p['completed']+=['Telephoto GNOME Camera preview and saved upright photo user-verified; v5 userspace persisted','Native LC898217XC driver adapted for Razer and position readback/optical movement verified']
p['evidence']+=['build/kali/telefocus-progress.json','test-runs/snapshot/fingerprint-inventory.txt']
(out/'camera-completion-progress.json').write_text(json.dumps(p,indent=2)+'\n')
