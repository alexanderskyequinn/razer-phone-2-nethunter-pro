from pathlib import Path
import json
root = Path(__file__).resolve().parents[1]
for name in ('pack_mainline_diagnostic.py', 'run_mainline_test.py', 'monitor_mainline_network.py'):
    path = root / 'tools' / name
    data = path.read_text().replace("'v6']", "'v6', 'v7']")
    if name == 'pack_mainline_diagnostic.py':
        data = data.replace("('v4', 'v5', 'v6')", "('v4', 'v5', 'v6', 'v7')")
        data = data.replace("if version == 'v6':", "if version in ('v6', 'v7'):")
        data = data.replace('Both original partitions must be restored afterward. Android slot A untouched.', 'Experimental boot_b/dtbo_b may remain installed per user instruction. Android slot A untouched.')
    path.write_bytes(data.encode())
path = root / 'diagnostic/mainline-init'
path.write_bytes(path.read_bytes().replace(b'DIAG_V6', b'DIAG_V7').replace(b'report-v6', b'report-v7'))
result = {'display': 'Framebuffer created and pattern write completed, but panel initialization command 0 returned -EINVAL; user observed initial artifacts then blank screen.', 'diagnosis': 'Panel prepare ran before DSI host power_on; add prepare_prev_first and attach secondary before primary.', 'network': 'Five HTTP reports retrieved', 'restoration': 'Not requested: user prefers keeping the experimental slot installed. Slot A remains original.', 'next_test': 'v7'}
(root / 'test-runs/mainline-v6/result.json').write_text(json.dumps(result, indent=2))
