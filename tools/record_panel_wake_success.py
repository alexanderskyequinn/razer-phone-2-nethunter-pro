"""Record the user-confirmed v20 wake fix, preserving rejected-test evidence."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
out = root / 'build/kali'
def read(path):
    return json.loads(path.read_text())
def write(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n')
wake = read(out / 'wake-progress.json')
wake.update(status='User confirms reliable lockscreen wake after v20 panel power timing correction. Three automated off/on cycles passed with normal runtime power management, no DPU timeouts or desktop restarts. User then repeated physical Power-button tests and confirmed fixed. Long-term testing remains.',
    candidate_status='Installed, boot readback and v19 rollback hashes verified; user-confirmed wake fix.',
    installed=True, user_confirmed=True,
    boot_id='111b94bd-c502-4554-a14a-ba3836600655',
    kernel_sha256='dd3b7156033e9db14bd9239c82a2906ff2008fe48f58a1ee5630a7f5d25b3bdd',
    kernel_directory='build/kali/panel-wake-kernel',
    normal_runtime_power_management=True)
wake['evidence'] += ['test-runs/kali-trial-v20/wake-auto-test.txt', 'test-runs/kali-trial-v20/final-check.txt']
write(out / 'wake-progress.json', wake)
manifest = read(out / 'boot-manifest-v20.json')
manifest['status'] = 'Installed; boot/rollback hashes verified; user confirms panel wake fix; full hardware regression not performed.'
write(out / 'boot-manifest-v20.json', manifest)
write(out / 'boot-manifest.json', manifest)
status = read(root / 'port-status.json')
status['current_followup']['wake'] = wake
status['current_followup']['boot'] = 'v20 kernel#13 booted, verified SHA and v19 rollback; user-confirmed display wake correction. Main camera and focus drivers initialize.'
status['current_followup']['next'] = 'Verify camera keyboard/photo viewing with user, then optical focus and autofocus integration. SIM remains deferred.'
status['status'] += ' v20 restores stock panel supply settling delays; automated wake tests pass with normal runtime PM and user confirms lockscreen wake fixed. Files installed and JPEG association configured; camera keyboard suppression installed. BU64753 focus driver initializes; optical focus/autofocus pending.'
write(root / 'port-status.json', status)
wifi = read(out / 'wifi-access.json')
wifi['limitations'] = 'Persistent selected-profile listener survived v20 reboot at user static192.0.2.78. Earlier manual static-address edit required rerunning helper; reapply-event handling remains unverified.'
wifi['evidence'].append('test-runs/kali-trial-v20/boot-health3.txt')
write(out / 'wifi-access.json', wifi)
