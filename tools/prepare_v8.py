from pathlib import Path
import json
root = Path(__file__).resolve().parents[1]
for name in ('pack_mainline_diagnostic.py', 'run_mainline_test.py', 'monitor_mainline_network.py'):
    path = root / 'tools' / name
    data = path.read_text().replace("'v7']", "'v7', 'v8']")
    data = data.replace("'v6', 'v7')", "'v6', 'v7', 'v8')")
    path.write_bytes(data.encode())
path = root / 'diagnostic/mainline-init'
text = path.read_text().replace('DIAG_V7', 'DIAG_V8').replace('report-v7', 'report-v8')
text = text.replace("echo; echo 'DRM state:'; cat /sys/kernel/debug/dri/*/state 2>/dev/null", "echo; echo 'DRM state:'; cat /sys/kernel/debug/dri/0/state 2>/dev/null\n        echo; echo 'Display clocks:'; grep -E 'dsi|mdss|mdp' /sys/kernel/debug/clk/clk_summary 2>/dev/null\n        echo; echo 'Backlight:'; for b in /sys/class/backlight/*; do cat \"$b/brightness\" \"$b/actual_brightness\" \"$b/bl_power\" 2>/dev/null; done\n        echo; echo 'Interrupt counters:'; cat /proc/interrupts")
path.write_bytes(text.encode())
result = {'panel_initialization': 'All 113 commands completed', 'framebuffer': '1440x2560 XR24 pattern write completed', 'display': 'User sees two thin horizontal colored bands repeating vertically in middle/right areas; no clear full-screen bars.', 'network': 'Five HTTP reports retrieved', 'bootloader_return': 'Automatic, verified at 2026-10-07T00:20:09Z', 'partition_state': 'Experimental v7 on boot_b and blank dtbo_b retained per user preference. Android A not booted or changed.', 'next_test': 'v8: match original 10-bpc DSC range_max_qp[0]=8, add encoder and clock diagnostics'}
(root / 'test-runs/mainline-v7/result.json').write_text(json.dumps(result, indent=2))
