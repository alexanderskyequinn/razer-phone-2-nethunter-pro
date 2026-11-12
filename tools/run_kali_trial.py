"""Validate, flash and start the explicitly authorized first native Kali trial."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import run_diagnostic_test as transport

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'build/kali'
transport.RUN = ROOT / 'test-runs/kali-trial-v1'
command = transport.command

def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def sparse_expanded_size(path):
    with path.open('rb') as stream:
        header = stream.read(28)
        magic, major, minor, hsize, csize, block, total, chunks, crc = struct.unpack('<I4H4I', header)
        assert magic == 0xED26FF3A and major == 1 and hsize >= 28 and csize >= 12 and block == 4096
        stream.seek(hsize)
        written = 0
        for _ in range(chunks):
            ch = stream.read(csize)
            kind, _, blocks, length = struct.unpack_from('<2H2I', ch)
            assert length >= csize
            payload = length - csize
            if kind == 0xCAC1:
                assert payload == blocks * block
            elif kind == 0xCAC2:
                assert payload == 4
            elif kind == 0xCAC3:
                assert payload == 0
            elif kind == 0xCAC4:
                assert blocks == 0 and payload == 4
            else:
                raise AssertionError('Unknown sparse chunk')
            written += blocks
            stream.seek(payload, 1)
        assert written == total and stream.tell() == path.stat().st_size
        return total * block

def validate():
    boot = json.loads((BUILD / 'boot-manifest.json').read_text())
    rootfs = json.loads((BUILD / 'rootfs-manifest.json').read_text())
    assert boot['identity'] == rootfs['identity']
    for name, record in boot['files'].items():
        assert Path(name).name == name
        path = BUILD / name
        assert path.stat().st_size == record['bytes'] and checksum(path) == record['sha256']
    sparse = BUILD / rootfs['sparse_file']
    assert sparse.name == rootfs['sparse_file']
    assert checksum(sparse) == rootfs['sparse_sha256']
    assert sparse.stat().st_size == rootfs['sparse_bytes']
    assert sparse_expanded_size(sparse) == rootfs['expanded_bytes']
    assert rootfs['filesystem_check_exit'] == 0
    assert (BUILD / 'roundtrip/kernel').read_bytes() == (BUILD / 'Image.gz-dtb').read_bytes()
    assert (BUILD / 'roundtrip/ramdisk').read_bytes() == (BUILD / 'initramfs.cpio.gz').read_bytes()
    assert (BUILD / 'blank-dtbo.img').read_bytes() == b'\0' * 8388608
    backup_dir = ROOT / 'device-data/20261006-181410-429985'
    backup = json.loads((backup_dir / 'manifest.json').read_text())
    for name in ('boot_a', 'boot_b', 'dtbo_a', 'dtbo_b', 'vbmeta_a', 'vbmeta_b'):
        path = backup_dir / (name + '.img')
        record = backup['files'][path.name]
        assert record['phone_sha256_verified'] and path.stat().st_size == record['bytes']
        assert checksum(path) == record['sha256']
    transport.save('validated-images', {'boot': boot, 'rootfs': rootfs})
    return rootfs

def size(name, text):
    match = re.search(r'partition-size:' + re.escape(name) + r':\s*(0x[0-9a-fA-F]+)', text)
    assert match, text
    return int(match.group(1), 16)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['validate', 'flash', 'start'])
    args = parser.parse_args()
    rootfs = validate()
    if args.phase == 'validate':
        print('Boot roundtrip, sparse structure, checksums, filesystem and recovery backups verified.')
        return
    assert 'product: cheryl2' in command('product', 'getvar', 'product')
    assert 'unlocked: yes' in command('unlocked', 'getvar', 'unlocked')
    if args.phase == 'flash':
        # Named partitions only; preserve GPT, boot A, modem and calibration.
        assert size('boot_b', command('boot-size', 'getvar', 'partition-size:boot_b')) == 67108864
        assert size('dtbo_b', command('dtbo-size', 'getvar', 'partition-size:dtbo_b')) == 8388608
        assert size('userdata', command('userdata-size', 'getvar', 'partition-size:userdata')) >= rootfs['expanded_bytes']
        command('flash-native-boot-b', 'flash', 'boot_b', str(BUILD / 'aura-kali-trial-v1.img'))
        command('flash-blank-dtbo-b', 'flash', 'dtbo_b', str(BUILD / 'blank-dtbo.img'))
        command('activate-native-b', 'set_active', 'b')
        assert 'current-slot: b' in command('native-slot', 'getvar', 'current-slot')
        transport.save('userdata-replacement-warning', {'user_authorized_erasure': True, 'do_not_boot_android': True})
        command('flash-kali-userdata', 'flash', 'userdata', str(BUILD / rootfs['sparse_file']), timeout=1200)
    else:
        for step in ('flash-native-boot-b', 'flash-blank-dtbo-b', 'flash-kali-userdata'):
            assert json.loads((transport.RUN / (step + '.json')).read_text())['code'] == 0
        assert 'current-slot: b' in command('slot-before-kali', 'getvar', 'current-slot')
        command('boot-native-kali', 'reboot')

if __name__ == '__main__':
    main()
