"""Exercise the real driver/library API with mocked sysfs and child responses."""
from pathlib import Path
import json
import os
import shlex
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
work = Path('/var/tmp/aura-libfprint-operations')
flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'glib-2.0', 'gio-2.0'], text=True))
subprocess.run(['gcc', '-Wall', '-Wextra', '-Werror', str(root/'tests/fprint-operations-test.c'),
    f'-I{work}/source', f'-I{work}/host/libfprint', *flags, f'-L{work}/host/libfprint',
    f'-Wl,-rpath,{work}/host/libfprint', '-lfprint-2', '-o', str(work/'operations-test')], check=True)
shutil.copy2(root/'tests/fprint_mock_bridge.py', work/'mock-bridge.py')
device = work/'device.umockdev'
device.write_text('''P: /devices/platform/fingerprint
E: SUBSYSTEM=platform
E: DRIVER=aura-fpc-resources
E: OF_COMPATIBLE_N=1
E: OF_COMPATIBLE_0=razer,aura-fpc-resources
A: modalias=of:NfingerprintT(null)Crazer,aura-fpc-resources
L: driver=../../../bus/platform/drivers/aura-fpc-resources

''')
scenarios = ['open-error', 'list-bad-id', 'list-wrong-account', 'list-duplicate',
    'verify-match', 'verify-no-match', 'verify-stale', 'verify-exit-fail', 'verify-double',
    'verify-no-result', 'verify-truncated', 'verify-flood', 'verify-nul', 'verify-cancel',
    'verify-wrong-metadata', 'verify-wrong-version', 'enroll-good', 'enroll-wrong-finger',
    'enroll-no-record', 'delete-good']
results = {}
for scenario in scenarios:
    (work/'scenario').write_text(scenario)
    result = subprocess.run(['umockdev-run', '--device', str(device), '--', str(work/'operations-test'), scenario],
        env=dict(os.environ, G_DEBUG='fatal-warnings'), capture_output=True, text=True, timeout=15)
    if result.returncode:
        print(result.stdout, result.stderr)
        raise SystemExit(f'{scenario}: failed {result.returncode}')
    print(f'{scenario}: passed')
    results[scenario] = 'passed'
(root/'build/kali/fingerprint/libfprint-operations-tests.json').write_text(json.dumps(results, indent=2)+'\n')
