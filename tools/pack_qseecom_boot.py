"""Build v26 with the experimental TEE kernel and exact repaired v25 ramdisk/DT."""
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tarfile
import zlib

root = Path(__file__).resolve().parents[1]
out = root / 'build/kali/qseecom-test'
out.mkdir(parents=True, exist_ok=True)
base = root / 'build/kali/power-recovery/aura-kali-v25-power-recovery.img'
assert hashlib.sha256(base.read_bytes()).hexdigest() == 'a4974b5902a4b335f95447f383e4790cf19c96d94d71ad95e2fed75fa9de4a79'
subprocess.run([sys.executable, str(root / 'sources/mkbootimg/unpack_bootimg.py'),
               '--boot_img', str(base), '--out', str(out / 'base')], check=True, stdout=subprocess.DEVNULL)
split = zlib.decompressobj(31)
split.decompress((out / 'base/kernel').read_bytes())
dtb = split.unused_data
assert dtb[:4] == b'\xd0\x0d\xfe\xed' and struct.unpack_from('>I', dtb, 4)[0] == len(dtb)
kernel = (root / 'build/kali/fingerprint-resources/Image-qseecom-experimental.gz').read_bytes()
assert hashlib.sha256(kernel).hexdigest() == '093d59e4c811ae9ab2c69801e0efbe51ec8b3aa31f198b4685872b97c1db0347'
assert gzip.decompress(kernel)[56:60] == b'ARM\x64'
(out / 'kernel-dtb').write_bytes(kernel + dtb)
image = out / 'aura-kali-v26-qseecom.img'
cmdline = json.loads((root / 'build/kali/boot-manifest-v25.json').read_text())['cmdline']
subprocess.run([sys.executable, str(root / 'sources/mkbootimg/mkbootimg.py'),
    '--kernel', str(out / 'kernel-dtb'), '--ramdisk', str(out / 'base/ramdisk'),
    '--header_version', '1', '--pagesize', '4096', '--base', '0', '--kernel_offset', '32768',
    '--ramdisk_offset', '16777216', '--tags_offset', '256', '--os_version', '9.0.0',
    '--os_patch_level', '2020-11', '--cmdline', cmdline, '--output', str(image)], check=True)
assert image.stat().st_size < 67108864
with image.open('ab') as f:
    f.write(b'\0' * (67108864-image.stat().st_size))
subprocess.run([sys.executable, str(root / 'sources/mkbootimg/unpack_bootimg.py'),
    '--boot_img', str(image), '--out', str(out / 'roundtrip')], check=True, stdout=subprocess.DEVNULL)
assert (out / 'roundtrip/kernel').read_bytes() == kernel + dtb
assert (out / 'roundtrip/ramdisk').read_bytes() == (out / 'base/ramdisk').read_bytes()

# Stock signed metadata/segments only; no persist data or biometric templates.
firmware = out / 'firmware'
firmware.mkdir(exist_ok=True)
files = {}
with tarfile.open(root / 'device-data/native-prerequisites/vendor-firmware.tar') as src:
    for stem, count in [('firmware/fpctzappfingerprint', 8), ('firmware_mnt/image/cmnlib', 6)]:
        for suffix in ['.mdt'] + [f'.b{i:02d}' for i in range(count)]:
            member = src.extractfile(stem + suffix)
            payload = member.read()
            dest = firmware / (Path(stem).name + suffix)
            dest.write_bytes(payload)
            files[dest.name] = hashlib.sha256(payload).hexdigest()
with tarfile.open(out / 'fingerprint-firmware.tar', 'w') as tar:
    for name in sorted(files):
        tar.add(firmware / name, arcname=name)
(out / 'firmware-sha256.txt').write_text(''.join(f'{sha}  {name}\n' for name, sha in files.items()))
record = {'version': 'v26-qseecom-test', 'image': str(image.relative_to(root)),
    'sha256': hashlib.sha256(image.read_bytes()).hexdigest(), 'bytes': image.stat().st_size,
    'base_sha256': hashlib.sha256(base.read_bytes()).hexdigest(),
    'ramdisk_unchanged_from_power_recovery': True, 'device_tree_unchanged': True,
    'gpio_driver_enabled': False, 'firmware_auto_loaded': False,
    'firmware_archive_sha256': hashlib.sha256((out / 'fingerprint-firmware.tar').read_bytes()).hexdigest(),
    'firmware_files': files, 'phone_installed': False}
(out / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({k: v for k, v in record.items() if k != 'firmware_files'}, indent=2))
