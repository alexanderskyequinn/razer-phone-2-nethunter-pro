"""Update diagnostic packaging for the bounded display test."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
for name in ('pack_mainline_diagnostic.py', 'run_mainline_test.py', 'monitor_mainline_network.py'):
    p = root / 'tools' / name
    text = p.read_text().replace("'v5']", "'v5', 'v6']")
    if name == 'pack_mainline_diagnostic.py':
        text = text.replace("('v4', 'v5')", "('v4', 'v5', 'v6')")
        text = text.replace("cpio=b''.join", "if version == 'v6':\n    entries.append(('bin/display-pattern',(OUT/'display-pattern').read_bytes(),0o100755,(0,0)))\ncpio=b''.join")
        text = text.replace('UNTESTED EXPERIMENTAL HEADLESS KERNEL DIAGNOSTIC', 'UNTESTED EXPERIMENTAL KERNEL DIAGNOSTIC')
        text = text.replace('RAM-only headless test', 'RAM-only hardware test')
    p.write_bytes(text.encode())
p = root / 'diagnostic/mainline-init'
text = p.read_text().replace('AURA_MAINLINE_DIAG_V5', 'AURA_MAINLINE_DIAG_V6').replace('aura-mainline-report-v5', 'aura-mainline-report-v6')
text = text.replace('snapshot() {', 'if [ -x /bin/display-pattern ]; then\n    /bin/display-pattern >/run/display-pattern.txt 2>&1 &\nfi\n\nsnapshot() {')
text = text.replace("echo; echo 'Display devices:';", "echo; echo 'Display pattern:'; cat /run/display-pattern.txt 2>/dev/null\n        echo; echo 'DRM state:'; cat /sys/kernel/debug/dri/*/state 2>/dev/null\n        echo; echo 'Display devices:';")
p.write_bytes(text.encode())
