#!/usr/bin/env python3
"""Package a RAM-only diagnostic boot image from a checksum-verified slot backup.

This creates files on the PC; it never invokes adb or fastboot.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib


def archive_entry(name, payload=b'', mode=0o100644, inode=1, rdev=(0, 0)):
    name_data = name.encode() + b'\0'
    fields = (inode, mode, 0, 0, 2 if mode & 0o170000 == 0o040000 else 1,
              0, len(payload), 0, 0, *rdev, len(name_data), 0)
    header = b'070701' + b''.join(f'{n:08x}'.encode() for n in fields)
    entry = header + name_data
    entry += b'\0' * (-len(entry) % 4)
    entry += payload
    entry += b'\0' * (-len(payload) % 4)
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    out = project / 'build/diagnostic'
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((args.capture / 'manifest.json').read_text())
    properties = (args.capture / 'properties.txt').read_text()
    if 'ro.product.device=aura' not in properties or 'ro.boot.slot_suffix=_a' not in properties:
        parser.error('This first diagnostic is reviewed only for the captured aura slot A configuration')
    boot = (args.capture / 'boot_a.img').read_bytes()
    backup = manifest['files']['boot_a.img']
    if not backup.get('phone_sha256_verified') or hashlib.sha256(boot).hexdigest() != backup['sha256']:
        parser.error('Slot A backup checksum is not verified')
    if boot[:8] != b'ANDROID!':
        parser.error('Not an Android boot image')
    kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size, second_addr, tags_addr, page_size, version, os_version = struct.unpack_from('<10I', boot, 8)
    if version != 1 or page_size != 4096 or second_size:
        parser.error('Unexpected boot image layout; manual review required')
    kernel = boot[page_size:page_size + kernel_size]
    decoder = zlib.decompressobj(31)
    raw = decoder.decompress(kernel)
    if not decoder.eof or b'want_initramfs\0' not in raw or b'skip_initramfs\0' in raw:
        parser.error('Expected existing Magisk skip_initramfs patch not found')
    if not decoder.unused_data.startswith(b'\xd0\x0d\xfe\xed'):
        parser.error('Expected appended device tree not found')
    busybox = (out / 'busybox').read_bytes()
    if busybox[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', busybox, 18)[0] != 183:
        parser.error('BusyBox is not a little-endian AArch64 ELF')
    phoff = struct.unpack_from('<Q', busybox, 32)[0]
    phsize, phnum = struct.unpack_from('<HH', busybox, 54)
    if any(struct.unpack_from('<I', busybox, phoff + i * phsize)[0] == 3 for i in range(phnum)):
        parser.error('BusyBox needs an external dynamic loader')

    init = (project / 'diagnostic/init').read_bytes().replace(b'\r\n', b'\n')
    entries = []
    for name in ('bin', 'dev', 'proc', 'sys', 'run', 'www', 'config'):
        entries.append((name, b'', 0o040755, (0, 0)))
    entries += [('bin/busybox', busybox, 0o100755, (0, 0)),
                ('bin/return-to-bootloader', (out / 'return-to-bootloader').read_bytes(), 0o100755, (0, 0)),
                ('bin/sh', b'busybox', 0o120777, (0, 0)),
                ('init', init, 0o100755, (0, 0)),
                ('report-template.img.gz', (out / 'report-template.img.gz').read_bytes(), 0o100644, (0, 0)),
                ('dev/console', b'', 0o020600, (5, 1)),
                ('dev/null', b'', 0o020666, (1, 3))]
    archive = b''.join(archive_entry(n, p, m, i, dev) for i, (n, p, m, dev) in enumerate(entries, 1))
    archive += archive_entry('TRAILER!!!')
    archive += b'\0' * (-len(archive) % 512)
    ramdisk = out / 'diagnostic.cpio.gz'
    ramdisk.write_bytes(gzip.compress(archive, mtime=0))
    kernel_path = out / 'existing-kernel-dtb'
    kernel_path.write_bytes(kernel)
    cmdline = (boot[64:576].split(b'\0', 1)[0] + boot[608:1632].split(b'\0', 1)[0]).decode()
    cmdline += ' rdinit=/init loglevel=7'
    image = out / 'aura-native-diag-v5-slot-b.img'
    args_pack = [sys.executable, str(project / 'sources/mkbootimg/mkbootimg.py'),
                 '--kernel', str(kernel_path), '--ramdisk', str(ramdisk),
                 '--header_version', '1', '--pagesize', str(page_size), '--base', '0',
                 '--kernel_offset', str(kernel_addr), '--ramdisk_offset', str(ramdisk_addr),
                 '--second_offset', str(second_addr), '--tags_offset', str(tags_addr),
                 '--os_version', '9.0.0', '--os_patch_level', '2020-11',
                 '--cmdline', cmdline, '--output', str(image)]
    subprocess.run(args_pack, check=True)
    # Replace the complete inactive boot partition, including its old AVB footer.
    partition_size = 67108864
    if image.stat().st_size > partition_size:
        parser.error('Diagnostic exceeds the confirmed boot partition size')
    with image.open('ab') as stream:
        stream.write(b'\0' * (partition_size - image.stat().st_size))
    report = {
        'status': 'UNTESTED ON DEVICE; diagnostic only, not NetHunter Pro',
        'image': image.name, 'bytes': image.stat().st_size,
        'sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
        'source_boot_sha256': backup['sha256'],
        'kernel_sha256': hashlib.sha256(kernel).hexdigest(),
        'busybox_sha256': hashlib.sha256(busybox).hexdigest(),
        'return_to_bootloader_sha256': hashlib.sha256((out / 'return-to-bootloader').read_bytes()).hexdigest(),
        'init_sha256': hashlib.sha256(init).hexdigest(),
        'intended_test': 'Inactive boot_b test only; preserve boot_a/dtbo/vbmeta. Restore active slot A and original boot_b after the test.',
        'expected_behavior': 'RAM-only PID1, USB NCM DHCP + read-only status.txt, return to fastboot after 180 seconds',
        'limits': 'USB enumeration, charging without Android, auto-reboot and bootloader acceptance remain untested. Screen may stay blank. Existing kernel is downstream 4.9, not mainline.'
    }
    (out / 'image-manifest.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
