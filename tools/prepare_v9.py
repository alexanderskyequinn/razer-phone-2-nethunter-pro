from pathlib import Path
root = Path(__file__).resolve().parents[1]
for name in ('pack_mainline_diagnostic.py', 'run_mainline_test.py', 'monitor_mainline_network.py'):
    path = root / 'tools' / name
    data = path.read_text().replace("'v8']", "'v8', 'v9']")
    data = data.replace("'v7', 'v8')", "'v7', 'v8', 'v9')")
    path.write_bytes(data.encode())
path = root / 'diagnostic/mainline-init'
text = path.read_text().replace('DIAG_V8', 'DIAG_V9').replace('report-v8', 'report-v9')
text = text.replace('for field in capacity voltage_now temp status; do', 'for field in capacity voltage_now current_now temp status temp_min temp_max temp_alert_min temp_alert_max; do')
text = text.replace('/sys/class/power_supply/battery/', '/sys/class/power_supply/qcom-battery/')
text = text.replace("echo; echo 'USB setup:';", "echo; echo 'Power supplies:'; for p in /sys/class/power_supply/*; do cat \"$p/uevent\" 2>/dev/null; done\n        echo; echo 'USB setup:';")
path.write_bytes(text.encode())
