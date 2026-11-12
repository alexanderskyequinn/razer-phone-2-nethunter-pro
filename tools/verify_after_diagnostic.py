"""Read Android restoration checksums and persistent logs without modifying it."""
import hashlib
import argparse
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--run', default='diag-v5-slot-b')
run = parser.parse_args().run
assert Path(run).name == run and run not in ('.', '..')
OUT = ROOT / 'test-runs' / run
OUT.mkdir(parents=True, exist_ok=True)
ADB = ['C:/adb/adb.exe', '-s', 'YOUR_DEVICE_SERIAL']


def read(command, root=False, binary=False):
    if root:
        command = 'su -c ' + shlex.quote(command)
    result = subprocess.run(ADB + (['exec-out'] if binary else ['shell', '-T']) + [command],
                            capture_output=True, timeout=35)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))
    return result.stdout


deadline = time.monotonic() + 35
while read('getprop sys.boot_completed').strip() != b'1':
    if time.monotonic() >= deadline:
        raise RuntimeError('Android boot is not complete yet; retry verification after startup')
    time.sleep(2)
slot = read('getprop ro.boot.slot_suffix').decode().strip()
assert slot == '_a', slot
assert b'uid=0' in read('id', root=True)
report = {'slot': slot, 'partitions': {}}
manifest = json.loads((ROOT / 'device-data/20261006-181410-429985/manifest.json').read_text())
for name in ('boot_a', 'boot_b', 'dtbo_a', 'dtbo_b', 'vbmeta_a', 'vbmeta_b'):
    digest = read('sha256sum /dev/block/bootdevice/by-name/' + name, root=True).decode().split()[0]
    report['partitions'][name] = {'sha256': digest, 'matches_original': digest == manifest['files'][name + '.img']['sha256']}
    (OUT / 'restoration-verification.json').write_text(json.dumps(report, indent=2))
    assert report['partitions'][name]['matches_original'], name
print('Android slot A restored. All six boot/dtbo/vbmeta partitions match the original verified backups.', flush=True)
for name, command in [('battery-after.txt', 'dumpsys battery'), ('dmesg-after.txt', 'dmesg'),
                      ('pstore-list.txt', 'ls -l /sys/fs/pstore')]:
    (OUT / name).write_bytes(read(command, root=True))
archive = read('tar -C /sys/fs/pstore -cf - .', root=True, binary=True)
(OUT / 'pstore-after.tar').write_bytes(archive)
with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
    for member in stream:
        if member.isfile():
            data = stream.extractfile(member).read()
            destination = OUT / ('pstore-' + Path(member.name).name)
            destination.write_bytes(data)
            lines = data.decode(errors='replace').splitlines()
            relevant = [line for line in lines if any(term in line.lower() for term in ('aura_native', 'udhcp', 'httpd', 'initramfs', 'panic', 'reboot:', 'permission denied', 'not found', 'failed'))]
            print(destination.name + '\n' + '\n'.join(relevant[-80:]), flush=True)
print((OUT / 'battery-after.txt').read_text())
