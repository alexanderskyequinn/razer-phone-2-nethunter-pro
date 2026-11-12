"""Record failed and pending wake experiments without labeling them fixed."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
out = root / 'build/kali'
status = json.loads((root / 'port-status.json').read_text())
result = {
    'status': 'Unresolved. User reports intermittent black screen on Power-button wake; rendered screenshot contains normal lockscreen. DPU frame timeouts also recorded. Runtime-power hold reduced logged timeouts but user reports every wake black; workaround disabled and removed from build overlay.',
    'rejected_workaround': 'aura-display-power.service disabled on phone; original runtime power/control=auto restored. Service files remain disabled for audit only.',
    'candidate': 'v20: restore exact stock VDDIO/IBB 20ms post-enable and EXCLK/VDDIO 1ms pre-disable delays. No kernel configuration change. Build release6.18.2-aura-bringup1+ matches installed modules.',
    'candidate_sha256': '3b7dd3eb53a8ca2fe3fda39380c61152975bdb785eb7a09fb4f7312d6478c59c',
    'candidate_status': 'Transferred and guarded update launched; reboot and wake verification pending.',
    'rollback': '/var/lib/aura/boot-v19-before-panel-wake.img',
    'stock_evidence': 'device-data/20261006-181410-429985/live.dts lines27790..27834',
    'evidence': ['test-runs/kali-trial-v19/wake-physical-result.txt', 'test-runs/kali-trial-v19/wake-runtime-auto-test.txt', 'test-runs/kali-trial-v19/wake-dpu-on-test.txt', 'test-runs/kali-trial-v19/wake-workaround-reverted.txt', 'test-runs/kali-trial-v19/aura-wake-frame.png', 'test-runs/kali-trial-v20/update-launch.txt']
}
(out / 'wake-progress.json').write_text(json.dumps(result, indent=2)+'\n')
status['current_followup']['wake'] = result
status['current_followup']['files'] = 'Nautilus and wlopm installed on phone and staged rootfs, dpkg audit clean. JPEG default set to Loupe and folders to Nautilus. User verification pending.'
(root / 'port-status.json').write_text(json.dumps(status, indent=2)+'\n')
