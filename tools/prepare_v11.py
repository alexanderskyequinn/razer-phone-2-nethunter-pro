from pathlib import Path
root = Path(__file__).resolve().parents[1]
for name in ('pack_mainline_diagnostic.py', 'run_mainline_test.py', 'monitor_mainline_network.py'):
    path = root / 'tools' / name
    data = path.read_text().replace("'v10']", "'v10', 'v11']")
    data = data.replace("'v9', 'v10')", "'v9', 'v10', 'v11')")
    if name == 'pack_mainline_diagnostic.py':
        data = data.replace("image=OUT/f'aura-mainline-diag-{version}.img'", "if version == 'v11':\n    for flag in ('clk_ignore_unused ', 'pd_ignore_unused ', 'regulator_ignore_unused '):\n        cmdline = cmdline.replace(flag, '')\nimage=OUT/f'aura-mainline-diag-{version}.img'")
    path.write_bytes(data.encode())
path = root / 'diagnostic/mainline-init'
path.write_bytes(path.read_bytes().replace(b'DIAG_V10', b'DIAG_V11').replace(b'report-v10', b'report-v11'))
