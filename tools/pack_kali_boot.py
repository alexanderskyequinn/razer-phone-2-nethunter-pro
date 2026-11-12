"""Package a bounded native Kali first boot; performs no device operations."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
from pack_diagnostic import archive_entry

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/kali'
KERNEL = ROOT / 'build/mainline'
DIAG = ROOT / 'build/diagnostic'
OUT.mkdir(parents=True, exist_ok=True)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', choices=['v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12', 'v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20', 'v21', 'v22', 'v23', 'v24', 'v25'], default='v6')
parser.add_argument('--kernel-dir', type=Path, default=KERNEL)
args = parser.parse_args()
version = args.version
KERNEL = args.kernel_dir.resolve()
identity = json.loads((OUT / 'identity.json').read_text())
init_source = ROOT / ('diagnostic/kali-persistent-init' if version in ('v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12', 'v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20', 'v21', 'v22', 'v23', 'v24', 'v25') else 'diagnostic/kali-init')
init = init_source.read_text().replace('@ROOT_UUID@', identity['root_uuid']).replace('@INSTALL_ID@', identity['install_id']).encode()
init = init.replace(b'AURA_KALI_V1', ('AURA_KALI_' + version.upper()).encode())
assert b'@ROOT_UUID@' not in init and b'@INSTALL_ID@' not in init
if version in ('v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12', 'v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20', 'v21', 'v22', 'v23', 'v24', 'v25'):
    init = init.replace(b'/bin/kali-watchdog &', b'# Persistent installation: no forced trial reboot.')
kernel = (KERNEL / 'Image.gz').read_bytes()
assert gzip.decompress(kernel)[56:60] == b'ARM\x64'
dtb = (KERNEL / 'sdm845-razer-aura.dtb').read_bytes()
assert dtb[:4] == b'\xd0\x0d\xfe\xed' and struct.unpack_from('>I', dtb, 4)[0] == len(dtb)
entries = [(p, b'', 0o040755, (0, 0)) for p in ('bin', 'dev', 'proc', 'sys', 'run', 'newroot')]
for name, path in [('busybox', DIAG / 'busybox'), ('return-to-bootloader', DIAG / 'return-to-bootloader'), ('kali-watchdog', OUT / 'kali-watchdog')]:
    elf = path.read_bytes()
    assert elf[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', elf, 18)[0] == 183
    phoff = struct.unpack_from('<Q', elf, 32)[0]
    size, count = struct.unpack_from('<HH', elf, 54)
    assert all(struct.unpack_from('<I', elf, phoff + i * size)[0] != 3 for i in range(count))
    entries.append(('bin/' + name, elf, 0o100755, (0, 0)))
entries.extend([('bin/sh', b'busybox', 0o120777, (0, 0)), ('init', init, 0o100755, (0, 0)), ('dev/console', b'', 0o020600, (5, 1)), ('dev/null', b'', 0o020666, (1, 3))])
if version in ('v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12', 'v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20', 'v21', 'v22', 'v23', 'v24', 'v25'):
    overlay = ROOT / 'port/kali-overlay'
    entries.append(('aura-overlay', b'', 0o040755, (0, 0)))
    for path in sorted(overlay.rglob('*')):
        rel = path.relative_to(overlay).as_posix()
        if version not in ('v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12', 'v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20', 'v21', 'v22', 'v23', 'v24', 'v25') and rel.startswith('etc/systemd/system/aura-first-boot-guard.service.d'):
            continue
        if path.is_dir():
            entries.append(('aura-overlay/' + rel, b'', 0o040755, (0, 0)))
        else:
            assert path.is_file() and not path.is_symlink()
            mode = 0o100755 if rel.startswith(('usr/local/sbin/', 'usr/local/bin/', 'etc/NetworkManager/dispatcher.d/')) else 0o100644
            entries.append(('aura-overlay/' + rel, path.read_bytes().replace(b'\r\n', b'\n'), mode, (0, 0)))
    if version in ('v11', 'v12', 'v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20', 'v21', 'v22', 'v23', 'v24', 'v25'):
        # Binary payload must not pass through text newline normalization.
        sensor = (OUT / 'sensor-proxy/iio-sensor-proxy').read_bytes()
        assert hashlib.sha256(sensor).hexdigest() == '2b463b420f69df81d43db795ce88caf12682909f165fe16b4168c4f098d87f89'
        entries.append(('aura-overlay/usr/local/libexec', b'', 0o040755, (0, 0)))
        entries.append(('aura-overlay/usr/local/libexec/aura-iio-sensor-proxy', sensor, 0o100755, (0, 0)))
if version in ('v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12', 'v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20', 'v21', 'v22', 'v23', 'v24', 'v25'):
    for directory in ('lib', 'lib/firmware', 'lib/firmware/qcom', 'lib/firmware/qcom/sdm845', 'lib/firmware/qcom/sdm845/razer', 'lib/firmware/qcom/sdm845/razer/aura'):
        entries.append((directory, b'', 0o040755, (0, 0)))
    for name in ('a630_sqe.fw', 'a630_gmu.bin'):
        entries.append(('lib/firmware/qcom/' + name, (OUT / 'upstream-gpu-firmware' / name).read_bytes(), 0o100644, (0, 0)))
    for name in ('a630_zap.mdt', 'a630_zap.b00', 'a630_zap.b01', 'a630_zap.b02'):
        entries.append(('lib/firmware/qcom/sdm845/razer/aura/' + name, (OUT / 'gpu-firmware' / name).read_bytes(), 0o100644, (0, 0)))
archive = b''.join(archive_entry(n, p, m, i, d) for i, (n, p, m, d) in enumerate(entries, 1)) + archive_entry('TRAILER!!!')
archive += b'\0' * (-len(archive) % 512)
(OUT / 'initramfs.cpio.gz').write_bytes(gzip.compress(archive, mtime=0))
(OUT / 'Image.gz-dtb').write_bytes(kernel + dtb)
cmdline = 'earlycon console=ttyMSM0,115200n8 rdinit=/init loglevel=7 printk.devkmsg=on fw_devlink=permissive panic=10 systemd.gpt_auto=0 systemd.repart=0'
image = OUT / ('aura-kali-trial-' + version + '.img')
subprocess.run([sys.executable, str(ROOT / 'sources/mkbootimg/mkbootimg.py'), '--kernel', str(OUT / 'Image.gz-dtb'), '--ramdisk', str(OUT / 'initramfs.cpio.gz'), '--header_version', '1', '--pagesize', '4096', '--base', '0', '--kernel_offset', '32768', '--ramdisk_offset', '16777216', '--tags_offset', '256', '--os_version', '9.0.0', '--os_patch_level', '2020-11', '--cmdline', cmdline, '--output', str(image)], check=True)
assert image.stat().st_size < 67108864
with image.open('ab') as f:
    f.write(b'\0' * (67108864 - image.stat().st_size))
(OUT / 'blank-dtbo.img').write_bytes(b'\0' * 8388608)
subprocess.run([sys.executable, str(ROOT / 'sources/mkbootimg/unpack_bootimg.py'), '--boot_img', str(image), '--out', str(OUT / 'roundtrip')], check=True, stdout=subprocess.DEVNULL)
assert (OUT / 'roundtrip/kernel').read_bytes() == kernel + dtb
assert (OUT / 'roundtrip/ramdisk').read_bytes() == (OUT / 'initramfs.cpio.gz').read_bytes()
files = [image, OUT / 'blank-dtbo.img', OUT / 'initramfs.cpio.gz', OUT / 'Image.gz-dtb']
manifest = {'version': version, 'identity': identity, 'cmdline': cmdline, 'scope': 'First Kali trial: read-only userdata lower filesystem, RAM overlay, ten-minute userspace guard and fifteen-minute initramfs watchdog', 'files': {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files}, 'status': 'Packaged and roundtrip verified; not boot-tested'}
if version in ('v4', 'v5'):
    manifest['scope'] = 'Persistent ext4 userdata root, with ten-minute userspace guard and fifteen-minute initramfs watchdog retained during bring-up'
if version in ('v6', 'v7', 'v8', 'v9', 'v10', 'v11', 'v12', 'v13', 'v14', 'v15', 'v16', 'v17', 'v18', 'v19', 'v20', 'v21', 'v22', 'v23', 'v24', 'v25'):
    manifest['scope'] = 'Persistent ext4 root, Adreno graphics acceleration, battery condition monitoring, no forced trial reboot timers'
(OUT / 'boot-manifest.json').write_text(json.dumps(manifest, indent=2))
(OUT / ('boot-manifest-' + version + '.json')).write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
