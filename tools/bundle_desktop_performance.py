"""Package the user-validated keyboard selection and stock CPU boost setting."""
import hashlib,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
overlay=root/'port/kali-overlay'
files=[('usr/local/sbin/aura-cpu-boost',0o755),('etc/systemd/system/aura-cpu-boost.service',0o644),('etc/systemd/user/mobi.phosh.OSK.service.d/30-aura-stevia.conf',0o644)]
archive_path=root/'build/kali/desktop-performance-fix.tar'
with tarfile.open(archive_path,'w') as archive:
    for name,mode in files:
        path=overlay/name
        info=archive.gettarinfo(str(path),arcname=name)
        info.uid=info.gid=0; info.uname=info.gname='root';info.mode=mode
        with path.open('rb') as stream: archive.addfile(info,stream)
manifest={
 'archive_sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),
 'files':[{'path':name,'sha256':hashlib.sha256((overlay/name).read_bytes()).hexdigest()} for name,_ in files],
 'cpu':'Global boost was disabled: maximum policy frequency 2649600 kHz. Enabled existing stock 2803200 kHz boost OPP. A two-second performance-governor ceiling check observed 2803200 kHz; restored schedutil automatically. Ordinary short workload peaked at 2649600 kHz. Dynamic scaling and all thermal protections retained; sustained boost endurance not tested.',
 'keyboard':'Official Kali phosh-osk-stevia 0.57.0-2 selected via drop-in, Squeekboard retained for rollback. User confirms keyboard hides correctly after rapid app switching.',
 'performance_feedback':'User reports app launches/swiping noticeably better after boost enabled and keyboard replacement.',
 'hardware_evidence':'All 8 CPU cores online; GPU FD630/Freedreno observed at 710 MHz. Two off-screen scenes 424/500 FPS. Correctly sized windowed vsync test 120 FPS; 478 delivered vblank events with median 8.31ms spacing. Storage direct read 259 MB/s; no active cooling limits or memory pressure in baseline.',
 'limitations':'These short tests do not prove every app stays smooth or isolate the cause of all perceived improvement. Early fullscreen benchmark invalidated by buffer dimensions not divisible by scale 3; excluded. Rotation crossfade is packaged separately.',
 'rollback':'Disable aura-cpu-boost.service and write 0 to /sys/devices/system/cpu/cpufreq/boost. Remove only 30-aura-stevia.conf and restart the user OSK service to restore Squeekboard.',
 'installed_state':'CPU boost oneshot enabled and active; persistent system-wide user OSK drop-in selects Stevia. Temporary OSK test drop-in removed. Local image-build root and package recipe updated. Reboot a7517520-8076-4a4b-8de7-dd5ce9acce16 verified boost=1, policy maximum 2803200 kHz, schedutil governor and active Stevia selected by persistent drop-in.',
 'launch_sample':'During user comparison, Settings startup acknowledgement took about 1 second and Firefox about 2 seconds, based on second-resolution Phosh app-tracker logs. This measures acknowledgement, not all content loading.',
 'evidence':['test-runs/kali-trial-v12/performance-baseline.txt','test-runs/kali-trial-v12/cpu-boost-verified.txt','test-runs/kali-trial-v12/cpu-stock-ceiling.txt','test-runs/kali-trial-v12/presentation-trace.txt','test-runs/kali-trial-v12/stevia-health.txt','test-runs/kali-trial-v12/desktop-performance-persistent.txt','test-runs/kali-trial-v12/crossfade-reboot-health-final.txt'],
}
archive_path.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(manifest['archive_sha256'])
