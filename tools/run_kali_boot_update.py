"""Install only the v2 trial boot update onto the existing Kali installation."""
import argparse
import hashlib
import json
from pathlib import Path
import run_diagnostic_test as transport

root = Path(__file__).resolve().parents[1]
build = root / 'build/kali'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('phase', choices=['validate', 'flash', 'start'])
parser.add_argument('--version', choices=['v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12'], default='v6')
args = parser.parse_args()
version = args.version
transport.RUN = root / ('test-runs/kali-trial-' + version)
manifest = json.loads((build / ('boot-manifest-' + version + '.json')).read_text())
assert manifest['version'] == version
assert manifest['identity'] == json.loads((build / 'rootfs-manifest.json').read_text())['identity']
for name, info in manifest['files'].items():
    assert Path(name).name == name
    path = build / name
    assert path.stat().st_size == info['bytes']
    with path.open('rb') as f:
        assert hashlib.file_digest(f, 'sha256').hexdigest() == info['sha256']
assert (build / 'roundtrip/kernel').read_bytes() == (build / 'Image.gz-dtb').read_bytes()
assert (build / 'roundtrip/ramdisk').read_bytes() == (build / 'initramfs.cpio.gz').read_bytes()
transport.save('validated-boot', manifest)
if args.phase == 'validate':
    print(f'Trial {version} image, roundtrip and installed filesystem identity verified.')
else:
    command = transport.command
    assert 'product: cheryl2' in command('product', 'getvar', 'product')
    assert 'current-slot: b' in command('slot', 'getvar', 'current-slot')
    if args.phase == 'flash':
        assert 'unlocked: yes' in command('unlocked', 'getvar', 'unlocked')
        assert '0x4000000' in command('boot-size', 'getvar', 'partition-size:boot_b')
        command('flash-kali-boot-' + version, 'flash', 'boot_b', str(build / ('aura-kali-trial-' + version + '.img')))
        command('reset-slot-retries', 'set_active', 'b')
    else:
        assert json.loads((transport.RUN / ('flash-kali-boot-' + version + '.json')).read_text())['code'] == 0
        command('boot-native-kali-' + version, 'reboot')
