import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / 'build/kali'
probe = json.loads((out / 'camera-probe-progress.json').read_text())
probe['recovery'] = 'Initial failed identification probe left file operations and normal reboot blocked. v22 transfer has not completed and its installer has not been run. User asked for hardware restart into Kali; probe is not auto-loaded.'
probe['next'] = ['Wait for Kali/Wi-Fi recovery', 'Complete v22 image and corrected probe transfer', 'Install and verify v22 with existing guarded scripts', 'Run corrected one-shot identification after clean-boot checks']
(out / 'camera-probe-progress.json').write_text(json.dumps(probe, indent=2) + '\n')
data = {
    'updated_utc': datetime.now(timezone.utc).isoformat(),
    'priority': ['complete camera support', 'fingerprint'],
    'status': 'Main rear autofocus installed and user verified. Telephoto/front identification awaiting clean restart after temporary probe fault; corrected module and CCI1 pin configuration built locally.',
    'completed': ['GNOME Camera live upright preview and photo thumbnail confirmed', 'Physical focus motor movement verified', 'Bounded contrast autofocus installed persistently; user confirms near/far focus', 'Retained original telephoto/front sensor tables decoded'],
    'remaining': ['Telephoto/front identification and capture', 'Telephoto focus and OIS investigation', 'Video recording and broader autofocus testing', 'Fingerprint'],
    'connection': probe['recovery'],
    'evidence': ['build/kali/autofocus-progress.json', 'build/kali/camera-probe-progress.json', 'test-runs/snapshot/autofocus-persist2.txt', 'test-runs/snapshot/camera-probe-fault.txt'],
}
(out / 'camera-completion-progress.json').write_text(json.dumps(data, indent=2) + '\n')
