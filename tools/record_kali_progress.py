"""Record the verified persistent and accelerated native installation."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
p = root / 'port-status.json'
s = json.loads(p.read_text())
final = (root / 'test-runs/kali-trial-v6/final-check.txt').read_text()
validation = (root / 'test-runs/kali-trial-v5-upstream-fw/fixed-size-validation.txt').read_text()
assert 'GL renderer: FD630' in final and '/var/lib/aura/persistence-probe: OK' in final
assert 'Environment=AURA_TRIAL_SECONDS=0' in final
assert validation.count('Validation: Success') == 3 and 'Validation: Failure' not in validation
s['status'] = 'Native Kali/Phosh with NetHunter GUI, persistent ext4 root, working Adreno 630 graphics, touch, keyboard and key-only USB SSH. V6 boots accelerated automatically; forced trial reboot timers removed.'
s['next_milestones'] = ['Port Wi-Fi and remaining peripherals', 'Validate sustained charging and long-term power management', 'Investigate compositor shutdown delay and remaining board integration warnings']
v = s['verified_on_phone']
v['slot'] = 'b'
v['kernel'] = '6.18.2-aura-bringup1+'
v['mainline_kernel'] = '6.18.2-aura-bringup1+; native Kali systemd on persistent ext4 userdata'
v['touch']['calibration'] = 'User confirmed accurate tapping, unlocking and swiping in Phosh'
v['battery'] = 'V3 showed modest net idle charging, 57 to 58 percent, 28 to 29.3 C. Sustained load charging remains unvalidated.'
s['fastboot_troubleshooting']['pending'] = None
s['mainline_bringup']['current_phone_state'] = 'Slot B native Kali persistent installation. Android userdata replaced; do not casually boot Android A.'
k = s['kali_image']
k['root_policy'] = 'V4 onward mounts the verified userdata ext4 root read-write; v5 reboot preserved probe checksum and installed packages'
k['persistence_evidence'] = 'test-runs/kali-trial-v5/gpu-first-check.txt'
k['boot_success'] = 'qbootctl marks B successful; layout verified unchanged across metadata update'
k['keyboard'] = 'Squeekboard service override working and user-confirmed'
k['nethunter'] = 'User-confirmed NetHunter 1.9.2 main GUI in v3; no attacks executed'
k['gpu'] = 'Freedreno FD630 / OpenGL ES 3.2 / Mesa 26.1.6. Phoc GLES2 at 1440x2560 119.802 Hz. Three fixed-size glmark2 pixel checks passed. User confirmed smoother correct graphics. V6 starts accelerated automatically.'
k['trial_limits'] = 'Removed in v6. Battery condition guard remains: 10..43 C, capacity at least 15%, charger health Good.'
k['gpu_firmware'] = 'Upstream SQE v2.07, stock/upstream-identical GMU, phone-specific signed zap firmware. Included in v6 initramfs.'
k['final_evidence'] = 'test-runs/kali-trial-v6/final-check.txt'
k['limitations'][0] = 'Long-term GPU stability not yet validated'
s['mainline_bringup']['state'] = 'Native Kali v6 persistent accelerated desktop verified'
s['mainline_bringup']['scope'] += ', Adreno 630 GPU/GMU with device-signed zap and upstream SQE'
s['compatibility_blockers']['current_kernel'] = 'Original Android kernel replaced in slot B by custom 6.18.2 kernel supporting current Kali/systemd/Mesa; board integration remains experimental.'
(root / 'test-runs/kali-trial-v6/result.json').write_text(json.dumps({'persistent_root': True, 'persistence_checksum_verified': True, 'boot_slot': 'b', 'boot_successful': True, 'renderer': 'FD630', 'desktop_renderer': 'gles2', 'opengl_es': '3.2', 'display': '1440x2560 @ 119.802 Hz', 'fixed_size_pixel_validations_passed': 3, 'user_reports_smoother_correct_graphics': True, 'usb_ssh': True, 'keyboard': True, 'forced_trial_reboot_timers': False, 'battery_condition_monitor': True, 'boot_manifest': 'build/kali/boot-manifest-v6.json'}, indent=2))
p.write_text(json.dumps(s, indent=2))
print('Recorded verified persistent accelerated Kali v6 milestones.')
