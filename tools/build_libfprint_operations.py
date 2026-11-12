"""Build isolated libfprint operations driver, keeping discovery artifacts intact."""
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
work = Path('/var/tmp/aura-libfprint-operations')
def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)
run(sys.executable, str(root/'tools/prepare_libfprint_platform.py'), '--operations')
common = ['-Ddrivers=aura_fpc', '-Dintrospection=false', '-Ddoc=false', '-Dinstalled-tests=false', '-Dudev_rules=disabled', '-Dudev_hwdb=disabled']
host = work/'host'
if not (host/'build.ninja').exists():
    run('meson', 'setup', str(host), str(work/'source'), *common,
        '-Dc_args=-DAURA_BRIDGE_TEST_ONLY')
else:
    run('meson', 'configure', str(host), '-Dc_args=-DAURA_BRIDGE_TEST_ONLY')
run('ninja', '-C', str(host), 'libfprint/libfprint-2.so.2.0.0')
if '--arm64' in sys.argv:
    arm = work/'arm64'
    if not (arm/'build.ninja').exists():
        run('meson', 'setup', str(arm), str(work/'source'), '--cross-file', '/var/tmp/aura-libfprint-platform/arm64.ini', *common)
    run('ninja', '-C', str(arm), 'libfprint/libfprint-2.so.2.0.0')
    out = root/'build/kali/fingerprint/libfprint-operations'
    out.mkdir(exist_ok=True)
    shutil.copy2(arm/'libfprint/libfprint-2.so.2.0.0', out/'libfprint-2.so.2')
print('Built isolated operations library')
