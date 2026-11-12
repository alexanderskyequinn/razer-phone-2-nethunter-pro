"""Record only verified camera milestones; retain wake/focus test limitations."""
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
out = root / 'build/kali'
def read(path):
    return json.loads(path.read_text())
def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')

archive = out / 'camera/aura-libcamera-v3-keyboard.tar.gz'
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest == '18e3db1f1f8ef839322cf638134dec53a16ac1827ed04b843bde22b5aad40d23'
shutil.copyfile(archive, out / 'camera/aura-libcamera.tar.gz')
userspace = read(out / 'camera/userspace-manifest.json')
userspace.update(archive_sha256=digest,
    status='v3 photo app installed: 3024x4024 portrait JPEG saves user-confirmed. SDL text-input suppression installed, user verification pending. Prior exposure/white-balance behavior retained.',
    photo_directory='/home/kali/Pictures/Camera',
    keyboard_fix_sha256='8598d892c2c16449fb0f7e1a9b81c21c7f9ee65b82c4a3ad69f2504928e9ece4')
userspace['evidence'] += ['test-runs/kali-trial-v18/photo-result2.txt', 'test-runs/kali-trial-v19/keyboard-install.txt']
write(out / 'camera/userspace-manifest.json', userspace)
focus = read(out / 'focus-progress.json')
focus.update(installed=True, boot_id='c09d7484-621f-4588-b29f-97ac73199aa9',
    status='v19 boot write/readback and v18 rollback verified by installer. BU64753 probe initialized successfully and registers lens subdev20. Optical movement and autofocus remain unverified.',
    evidence=['test-runs/kali-trial-v19/wake-diagnosis-current-ip.txt', 'test-runs/kali-trial-v19/wake-details.txt'])
write(out / 'focus-progress.json', focus)
camera = read(out / 'camera-progress.json')
camera.update(userspace=userspace, focus=focus,
    status='Main rear live preview, portrait output, exposure and smoothed white balance user-verified. PHOTO shutter writes portrait JPEGs; user confirms SAVED. Camera keyboard fix installed, awaiting user check. Focus driver probes under v19; optical movement and autofocus not tested.',
    limitations='Autofocus, OIS, telephoto and calibrated colors/exposure timing pending. Saved JPEG portrait conversion passes synthetic test; user photo viewing check pending. Front camera already failed under Android.',
    scope='Main rear IMX363 and BU64753 focus controller on CCI0. Telephoto/front/OIS remain unconfigured.')
write(out / 'camera-progress.json', camera)
wifi = read(out / 'wifi-access.json')
wifi['limitations'] = 'Key-only profile-scoped listener verified after v19 reboot at DHCP address192.0.2.98. User then set static192.0.2.78; manually refreshed helper to restore listener. Static reapply event handling needs review.'
write(out / 'wifi-access.json', wifi)
status = read(root / 'port-status.json')
status['current_followup'] = {
    'boot': 'v19 booted, focus driver initialized; optical focus not tested',
    'camera': camera['status'],
    'files': 'Nautilus and wlopm installed successfully; Loupe already installed. User photo viewing check pending.',
    'wake': 'User reports intermittent black screen on wake. DPU kickoff timeouts recorded while Phosh remained running; no full system suspend in this boot. Output-disable diagnostic triggered Phosh disconnect/restart, ordinary DPMS test rejected by compositor. Physical Power-button trace pending.',
    'network': 'User-configured static 192.0.2.78; existing trusted Wi-Fi SSH works.'}
write(root / 'port-status.json', status)
