import json
from pathlib import Path
from datetime import datetime, timezone
root=Path(__file__).resolve().parents[1]
out=root/'build/kali'
now=datetime.now(timezone.utc).isoformat()
p=json.loads((out/'telecamera-progress.json').read_text())
p.update(updated_utc=now, status='v23 boot verified. IMX351 raw capture delivers4208x3120 at30fps; high-sensitivity frame visually contains scene. Kernel module persisted. Isolated libcamera helper enumerates both rear cameras; GNOME Camera trial open, user preview/photo validation pending.',capture_verified=True, app_user_verified=False, module_persistent=True, userspace_persistent=False)
p['evidence']=['test-runs/snapshot/telecamera-first-boot.txt','test-runs/snapshot/telecamera-first-capture.txt','test-runs/snapshot/telecamera-debug-capture.txt','test-runs/snapshot/telecamera-high-gain.png','test-runs/snapshot/telecamera-high-gain-statistics.txt','test-runs/snapshot/telecamera-userspace-enumeration.txt','test-runs/snapshot/telecamera-app-trial.txt','test-runs/snapshot/telecamera-persist-module.txt']
p['limitations']=['Initial1800line1xgain8framecapture was black;3178line8xgain61framecapture shows scene. Separate gain and startup-settling effects remain to characterize.','No telephoto focus driver installed yet','App preview/photo check pending','Front sensor still returnsENXIO with100msresetsettle and20msrailwaits','Calibration, OIS and video tests incomplete']
p['userspace_trial']={'prefix':'/opt/aura-camera-tele-test','archive':'build/kali/camera/aura-libcamera-tele-trial.tar.gz','sha256':'e6f682ef503452519f8607832419e1722b9d552f8792fa089f390376644f8551','dropins':'/run/user/1000/systemd/user/{pipewire,wireplumber}.service.d/80-aura-tele-trial.conf','canonical_autofocus_archive_unchanged':True}
p['next_focus_candidate']={'compiled':True,'installed':False,'module':'build/kali/telefocus/lc898217.ko','module_sha256':'d13818c0dfc828ace4ea6508fd6c79e8d28800e559f11895e6c06da0c7fa282e','dtb_sha256':'72ea764c0393d43fdc639b2d3f1c0406d1ca08daf9d9472ad723adf6491a1969','notes':'StockLC898217XC atCCI1:0x72,VAFviaTLMM99/BOB;ID0xf0=0x72,init0xe0=1,poll0xe3=0,focusword0x84range60..610. Not yet exercised. No v24boot packaged.'}
(out/'telecamera-progress.json').write_text(json.dumps(p,indent=2)+'\n')
c=json.loads((out/'camera-completion-progress.json').read_text())
c.update(updated_utc=now,status=p['status'],connection='Authorized Wi-Fi SSH192.0.2.78 works; no temporary2222 listener needed after reset.')
c['completed']+=['IMX351 identity verified and full-resolution raw image captured; module persisted','Telephoto libcamera helper built and both rear cameras enumerated','Front identification retried conservatively;noacknowledgement;testcleanlyunloaded']
c['remaining']=['User telephoto app preview/photo check; promote userspace trial if successful','Install/test preparedLC898217XCtelefocuscandidate and integrateboundedAF','Investigatefrontsensorphysical/powerfailure withoutassumingsoftware-onlycause','OIS and video testing','Fingerprint after cameras']
c['evidence']+=['build/kali/telecamera-progress.json','test-runs/snapshot/front-camera-relaxed-retry.txt']
(out/'camera-completion-progress.json').write_text(json.dumps(c,indent=2)+'\n')
