#!/usr/bin/env python3
"""Read-only Razer Phone 2 inventory and optional boot-partition backup.

Writes only to the PC. Never reboots, flashes, erases, mounts, or pushes files.
Root reads can cause a Magisk authorization prompt on the phone.
"""
import argparse
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adb', default=shutil.which('adb'))
    parser.add_argument('--serial', help='Required if more than one device is attached')
    parser.add_argument('--backup-boot', action='store_true', help='Read both boot/dtbo/vbmeta slots; requires root')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'device-data')
    args = parser.parse_args()
    if not args.adb:
        parser.error('adb was not found')
    devices = subprocess.run([args.adb, 'devices'], capture_output=True, text=True, check=True, timeout=15)
    entries = [line.split()[:2] for line in devices.stdout.splitlines()[1:] if len(line.split()) >= 2]
    ready = [serial for serial, state in entries if state == 'device']
    if args.serial:
        if args.serial not in ready:
            parser.error('The selected phone is absent or has not authorized USB debugging')
        serial = args.serial
    elif len(ready) == 1:
        serial = ready[0]
    else:
        parser.error('Connect and authorize exactly one phone, or select one with --serial')
    adb = [args.adb, '-s', serial]

    def run(command, root=False, timeout=30, binary=False):
        if root:
            command = 'su -c ' + shlex.quote(command)
        # shell v2 preserves remote exit status and separates stderr. exec-out is
        # used only for binary streams, whose format/length is checked separately.
        transport = ['exec-out'] if binary else ['shell', '-T']
        return subprocess.run(adb + transport + [command], capture_output=True, timeout=timeout)

    model = run('getprop ro.product.model').stdout.decode(errors='replace').strip()
    product = run('getprop ro.product.device').stdout.decode(errors='replace').strip()
    if product.lower() not in ('aura', 'cheryl2') and model.lower() not in ('phone 2', 'razer phone 2'):
        parser.error(f'Unexpected device: {model!r} / {product!r}; refusing to collect')
    out = args.output / dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    out.mkdir(parents=True, exist_ok=False)
    manifest = {'model': model, 'product': product, 'created': dt.datetime.now(dt.timezone.utc).isoformat(), 'files': {}, 'errors': []}

    def save_manifest():
        (out / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

    def save(name, data):
        (out / name).write_bytes(data)
        manifest['files'][name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        save_manifest()

    def collect(name, command, root=False):
        try:
            result = run(command, root=root, binary=name.endswith(('.gz', '.dtb', '.tar')))
            if result.returncode != 0 or not result.stdout:
                raise RuntimeError(result.stderr.decode(errors='replace').strip() or f'exit {result.returncode}, no data')
            save(name, result.stdout)
            return result.stdout
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            manifest['errors'].append(f'{name}: {exc}')
            save_manifest()
            return None

    properties = [
        'ro.product.model', 'ro.product.device', 'ro.product.board',
        'ro.build.fingerprint', 'ro.build.version.release', 'ro.build.version.security_patch',
        'ro.boot.slot_suffix', 'ro.boot.hardware', 'ro.boot.hardware.sku',
        'ro.boot.verifiedbootstate', 'ro.boot.flash.locked', 'ro.boot.bootloader',
    ]
    command = '; '.join(f'printf "{p}="; getprop {p}' for p in properties)
    collect('properties.txt', command)
    for name, command in {
        'kernel.txt': 'uname -a',
        'partitions.txt': 'cat /proc/partitions',
        'input-devices.txt': 'cat /proc/bus/input/devices',
        'battery.txt': 'dumpsys battery',
        'mounts.txt': 'cat /proc/mounts',
        'usb.txt': 'ls -l /sys/class/udc',
    }.items():
        collect(name, command)
    print('Reading root diagnostics; allow the ADB shell in Magisk if prompted.', flush=True)
    result = run('id', root=True, timeout=60)
    if result.returncode != 0 or b'uid=0' not in result.stdout:
        manifest['errors'].append('Root access unavailable; root diagnostics and backups were not collected')
        save_manifest()
        print(f'Basic inventory saved: {out}\nRoot access is needed to continue.')
        return 2
    for name, command in {
        'cmdline.txt': 'cat /proc/cmdline',
        'partition-links.txt': 'ls -l /dev/block/bootdevice/by-name',
        'dmesg.txt': 'dmesg',
        'iomem.txt': 'cat /proc/iomem',
        'live-device-tree.tar': 'tar -C /sys/firmware/devicetree/base -cf - .',
        'live.dtb': 'cat /sys/firmware/fdt',
    }.items():
        collect(name, command, root=True)
    config = collect('config.gz', 'cat /proc/config.gz', root=True)
    if config:
        try:
            save('kernel.config', gzip.decompress(config))
        except (OSError, EOFError) as exc:
            manifest['errors'].append(f'Cannot decode kernel configuration: {exc}')

    failures = 0
    if args.backup_boot:
        for partition in ('boot_a', 'boot_b', 'dtbo_a', 'dtbo_b', 'vbmeta_a', 'vbmeta_b'):
            device_path = '/dev/block/bootdevice/by-name/' + partition
            print(f'Backing up {partition} to the PC...', flush=True)
            try:
                size_result = run('blockdev --getsize64 ' + device_path, root=True)
                if size_result.returncode:
                    raise RuntimeError('Cannot determine partition size')
                size = int(size_result.stdout.strip())
                if not 0 < size <= 128 * 1024 * 1024:
                    raise RuntimeError(f'Unexpected partition size: {size}')
                result = run('cat ' + device_path, root=True, timeout=180, binary=True)
                if result.returncode or len(result.stdout) != size:
                    raise RuntimeError(f'Incomplete transfer ({len(result.stdout)} of {size} bytes)')
                phone_hash = run('sha256sum ' + device_path, root=True, timeout=60)
                digest = hashlib.sha256(result.stdout).hexdigest()
                expected = phone_hash.stdout.decode(errors='replace').split()
                if phone_hash.returncode or not expected or not re.fullmatch('[0-9a-fA-F]{64}', expected[0]) or expected[0].lower() != digest:
                    raise RuntimeError('Phone and PC checksums could not be verified')
                save(partition + '.img', result.stdout)
                manifest['files'][partition + '.img']['phone_sha256_verified'] = True
                save_manifest()
            except (RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
                failures += 1
                manifest['errors'].append(f'{partition}: {exc}')
                save_manifest()
                print(f'  Backup failed: {exc}', flush=True)
    save_manifest()
    print(f'Saved: {out}')
    print(f'{len(manifest["files"])} files; {len(manifest["errors"])} collection warnings; {failures} failed partition backups.')
    print('These boot backups are not a full Android or personal-data backup.')
    return 2 if failures else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (subprocess.SubprocessError, OSError) as exc:
        sys.exit(f'Collection stopped: {exc}')
