"""Run the reviewed, bounded v5 diagnostic and retain recovery records."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'device-data/20261006-181410-429985'
BUILD = ROOT / 'build/diagnostic'
RUN = ROOT / 'test-runs/diag-v5-slot-b'
FB = ROOT / 'tools/platform-tools-30.0.5/platform-tools/fastboot.exe'
SERIAL = 'YOUR_DEVICE_SERIAL'
IMAGE_HASH = '7154d680f565124236d9ea5d976cbe7f23de17916ab8f38974d8301adae257e9'


def save(name, data):
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / (name + '.json')).write_text(json.dumps(data, indent=2))


def command(name, *args, timeout=40):
    record = {'time': datetime.now(timezone.utc).isoformat(), 'args': list(args)}
    save(name + '-intent', record)
    try:
        result = subprocess.run([str(FB), '-s', SERIAL, *args], capture_output=True, timeout=timeout)
        record.update(code=result.returncode, text=(result.stdout + result.stderr).decode(errors='replace'))
    except subprocess.TimeoutExpired:
        record.update(code=None, text='TIMEOUT: device state must be inspected before continuing')
    save(name, record)
    print(json.dumps(record), flush=True)
    if record['code'] != 0:
        raise RuntimeError('Fastboot operation failed: ' + name)
    return record['text']


def validate():
    manifest = json.loads((CAPTURE / 'manifest.json').read_text())
    for filename in ('boot_a.img', 'boot_b.img', 'dtbo_a.img', 'dtbo_b.img', 'vbmeta_a.img', 'vbmeta_b.img'):
        payload = (CAPTURE / filename).read_bytes()
        item = manifest['files'][filename]
        assert item['phone_sha256_verified']
        assert len(payload) == item['bytes']
        assert hashlib.sha256(payload).hexdigest() == item['sha256']
    image = (BUILD / 'aura-native-diag-v5-slot-b.img').read_bytes()
    assert len(image) == 67108864 and hashlib.sha256(image).hexdigest() == IMAGE_HASH
    assert (BUILD / 'roundtrip-v5/kernel').read_bytes() == (BUILD / 'existing-kernel-dtb').read_bytes()
    assert (BUILD / 'roundtrip-v5/ramdisk').read_bytes() == (BUILD / 'diagnostic.cpio.gz').read_bytes()
    data = gzip.decompress((BUILD / 'roundtrip-v5/ramdisk').read_bytes())
    entries = {}
    pos = 0
    while True:
        assert data[pos:pos+6] == b'070701'
        fields = [int(data[pos+6+i*8:pos+14+i*8], 16) for i in range(13)]
        mode, size, namesize = fields[1], fields[6], fields[11]
        name = data[pos+110:pos+110+namesize-1].decode()
        pos = (pos + 110 + namesize + 3) & ~3
        payload = data[pos:pos+size]
        pos = (pos + size + 3) & ~3
        if name == 'TRAILER!!!':
            break
        entries[name] = (mode, payload)
    assert entries['init'] == (0o100755, (ROOT / 'diagnostic/init').read_bytes().replace(b'\r\n', b'\n'))
    assert entries['bin/sh'] == (0o120777, b'busybox')
    for name in ('busybox', 'return-to-bootloader'):
        mode, elf = entries['bin/' + name]
        assert mode == 0o100755 and elf == (BUILD / name).read_bytes()
        assert elf[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', elf, 18)[0] == 183
        offset = struct.unpack_from('<Q', elf, 32)[0]
        step, count = struct.unpack_from('<HH', elf, 54)
        assert all(struct.unpack_from('<I', elf, offset+i*step)[0] != 3 for i in range(count))
    save('validation', {'passed': True, 'image_sha256': IMAGE_HASH, 'entries': list(entries),
                        'restore_image': str(CAPTURE / 'boot_b.img')})
    print('Image roundtrip, initramfs payloads, static ARM64 binaries, and all six recovery backups validated.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['validate', 'flash', 'start', 'monitor', 'restore'])
    phase = parser.parse_args().phase
    if phase == 'validate':
        validate()
    elif phase == 'flash':
        validate()
        assert 'product: cheryl2' in command('product', 'getvar', 'product')
        assert 'current-slot: a' in command('slot-before', 'getvar', 'current-slot')
        assert 'unlocked: yes' in command('unlocked', 'getvar', 'unlocked')
        assert '0x4000000' in command('boot-b-size', 'getvar', 'partition-size:boot_b')
        command('flash-diagnostic-boot-b', 'flash', 'boot_b', str(BUILD / 'aura-native-diag-v5-slot-b.img'))
    elif phase == 'start':
        assert json.loads((RUN / 'flash-diagnostic-boot-b.json').read_text())['code'] == 0
        assert 'current-slot: a' in command('slot-before-start', 'getvar', 'current-slot')
        command('activate-b', 'set_active', 'b')
        assert 'current-slot: b' in command('slot-test', 'getvar', 'current-slot')
        command('reboot-diagnostic', 'reboot')
    elif phase == 'monitor':
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        end = time.monotonic() + 25
        last = ''
        while time.monotonic() < end:
            try:
                with opener.open('http://169.254.84.5/status.txt', timeout=2) as response:
                    status = response.read(4*1024*1024)
                if status.startswith(b'AURA_NATIVE_DIAG_V5'):
                    (RUN / 'native-status.txt').write_bytes(status)
                    print(status[:3500].decode(errors='replace'))
                    return
            except Exception as error:
                last = str(error)
            time.sleep(2)
        print('No diagnostic HTTP response yet: ' + last)
        result = subprocess.run([str(FB), 'devices'], capture_output=True, timeout=5)
        print('Fastboot devices: ' + result.stdout.decode(errors='replace'))
    elif phase == 'restore':
        validate()
        assert 'product: cheryl2' in command('restore-product', 'getvar', 'product')
        command('restore-active-a', 'set_active', 'a')
        assert 'current-slot: a' in command('restore-slot', 'getvar', 'current-slot')
        command('restore-original-boot-b', 'flash', 'boot_b', str(CAPTURE / 'boot_b.img'))
        command('reboot-original-android', 'reboot')


if __name__ == '__main__':
    main()
