"""Save device firmware and calibration data locally, without phone writes."""
from pathlib import Path
import hashlib
import io
import json
import shlex
import subprocess
import tarfile
import time

root = Path(__file__).resolve().parents[1]
out = root / 'device-data/native-prerequisites'
out.mkdir(parents=True, exist_ok=True)
adb = ['C:/adb/adb.exe', '-s', 'YOUR_DEVICE_SERIAL']

def read(command, timeout=60):
    p = subprocess.run(adb + ['exec-out', 'su -c ' + shlex.quote(command)], capture_output=True, timeout=timeout, check=True)
    return p.stdout

assert b'uid=0' in read('id')
assert read('getprop ro.boot.slot_suffix').strip() == b'_a'
manifest = {}
for name, command in {
    'vendor-firmware.tar': 'tar -C /vendor -cf - firmware firmware_mnt/image etc/wifi',
    'persist-calibration.tar': 'tar -C /mnt/vendor/persist -cf - .',
    'pstore-v8.tar': 'tar -C /sys/fs/pstore -cf - .',
}.items():
    data = read(command, timeout=180)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        files = [{ 'name': m.name, 'size': m.size } for m in archive if m.isfile()]
    assert files, name
    (out / name).write_bytes(data)
    manifest[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'files': files}
    print(name, len(data), len(files), 'files', flush=True)
for name, command in {
    'battery.txt': 'dumpsys battery',
    'power-supply.txt': 'for p in /sys/class/power_supply/*; do echo "$p"; cat "$p/uevent"; done',
    'firmware-symlinks.txt': 'find /vendor/firmware -type l -exec ls -l {} \\;',
    'mounts.txt': 'cat /proc/mounts',
    'partitions.txt': 'ls -l /dev/block/bootdevice/by-name; cat /proc/partitions',
}.items():
    (out / name).write_bytes(read(command))
expected = json.loads((root / 'test-runs/mainline-v8/artifacts/image-manifest.json').read_text())['files']
original = json.loads((root / 'device-data/20261006-181410-429985/manifest.json').read_text())['files']
partitions = {}
for name in ('boot_a', 'dtbo_a', 'vbmeta_a', 'vbmeta_b', 'boot_b', 'dtbo_b'):
    digest = read('sha256sum /dev/block/bootdevice/by-name/' + name).decode().split()[0]
    intended = expected['aura-mainline-diag-v8.img']['sha256'] if name == 'boot_b' else expected['blank-dtbo.img']['sha256'] if name == 'dtbo_b' else original[name + '.img']['sha256']
    partitions[name] = {'sha256': digest, 'matches_intended': digest == intended}
    assert digest == intended, name
manifest['partition_state'] = partitions
(out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
print('Firmware, calibration, successful display logs, and intended partition state verified.', flush=True)
