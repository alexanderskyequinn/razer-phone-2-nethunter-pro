import hashlib
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = [
 'etc/systemd/user/pipewire.service.d/60-aura-camera.conf',
 'etc/systemd/user/wireplumber.service.d/60-aura-camera.conf',
 'usr/share/applications/aura-camera.desktop',
]
archive = root / 'build/kali/snapshot-integration.tar'
with tarfile.open(archive, 'w') as tar:
    for path in paths:
        tar.add(root / 'port/kali-overlay' / path, arcname=path)
record = {
 'updated_utc': datetime.now(timezone.utc).isoformat(),
 'status': 'GNOME Snapshot 50.0 installed and integrated. User confirms live upright preview, photo capture and thumbnail viewing work; focus remains nonfunctional. Persistent media-service configuration passes service-restart test with active camera stream and no failed system units.',
 'user_confirmed': ['live preview', 'upright orientation', 'photo capture', 'thumbnail viewing'],
 'remaining': ['Autofocus is not implemented; optical lens movement not verified.', 'Video recording and playback not tested.', 'New integration has survived media-service restart, not yet a full phone reboot.'],
 'integration': 'Official system libcamera/PipeWire plugins use the existing private libcamera 0.7.2 through service-scoped environment. No system libraries replaced. Camera runs GPU soft ISP on Adreno FD630. Sensor rotation metadata is exposed as90.',
 'desktop': 'Camera (org.gnome.Snapshot); older diagnostic app retained but hidden from launcher.',
 'rollback': 'Remove only 60-aura-camera.conf from pipewire/wireplumber user service drop-ins, reload and restart these services. Restore /var/lib/aura/aura-camera-before-snapshot.desktop if the diagnostic launcher is needed. Private camera binaries remain available.',
 'evidence': ['test-runs/snapshot/trial.txt', 'test-runs/snapshot/open.txt', 'test-runs/snapshot/health.txt', 'test-runs/snapshot/persist.txt', 'test-runs/snapshot/finalize.txt'],
 'archive': str(archive.relative_to(root)),
 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
 'rootfs': 'Package recipe, overlay and local rootfs staging updated; package audit clean. Full install image not rebuilt.',
}
(root / 'build/kali/snapshot-progress.json').write_text(json.dumps(record, indent=2) + '\n')
path = root / 'port-status.json'
data = json.loads(path.read_text(encoding='utf-8'))
data['current_followup']['snapshot'] = record
data['current_followup']['hardware_audit'] = 'build/kali/hardware-audit.json (reconciled current audit; historical milestone entries below may describe earlier states)'
hp = data['hardware_progress']
hp['verified']['standard_camera_app'] = record['status']
hp['not_ported'] = ['telephoto/front camera and OIS', 'fingerprint', 'USB host/type-C roles']
hp['detected_not_functionally_verified'] = [s for s in hp['detected_not_functionally_verified'] if s != 'microSD controller']
hp['blocked']['camera_completion'] = 'Main rear still photography works in GNOME Snapshot. Focus, OIS, telephoto, calibrated image quality and video validation remain. Front camera already failed in Android.'
path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
path = root / 'build/kali/camera-progress.json'
camera = json.loads(path.read_text())
camera['status'] = record['status']
camera['standard_app'] = record
path.write_text(json.dumps(camera, indent=2) + '\n')
print('Snapshot milestone and status records updated.')
