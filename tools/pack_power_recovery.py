"""Patch only the guard in the verified v25 ramdisk; preserve its kernel/DT."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
source = root / 'build/kali/aura-kali-trial-v25.img'
out = root / 'build/kali/power-recovery'
out.mkdir(parents=True, exist_ok=True)
assert hashlib.sha256(source.read_bytes()).hexdigest() == '571e3302fd053920dc178c495a6267addd9f5827ed132b37d09b6f51ef37d502'
subprocess.run([sys.executable, str(root / 'sources/mkbootimg/unpack_bootimg.py'),
                '--boot_img', str(source), '--out', str(out / 'original')], check=True, stdout=subprocess.DEVNULL)

def entries(data):
    pos = 0
    while True:
        start = pos
        header = data[pos:pos+110]
        assert header[:6] == b'070701'
        fields = [int(header[6+i*8:14+i*8], 16) for i in range(13)]
        name = data[pos+110:pos+110+fields[11]-1].decode()
        content = (pos+110+fields[11]+3) & ~3
        pos = (content+fields[6]+3) & ~3
        yield name, fields, data[content:content+fields[6]], data[start:pos], content-start
        if name == 'TRAILER!!!':
            break

archive = gzip.decompress((out / 'original/ramdisk').read_bytes())
target = 'aura-overlay/usr/local/sbin/aura-first-boot-guard'
replacement = (root / 'port/kali-overlay/usr/local/sbin/aura-first-boot-guard').read_bytes().replace(b'\r\n', b'\n')
old = {}
chunks = []
changed = []
for name, fields, payload, raw, offset in entries(archive):
    old[name] = (fields, payload)
    if name == target:
        assert b'[ "$capacity" -lt 15 ] ||' in payload
        header = bytearray(raw[:offset])
        header[54:62] = f'{len(replacement):08x}'.encode()
        raw = bytes(header) + replacement
        raw += b'\0' * (-len(raw) % 4)
        changed.append(name)
    chunks.append(raw)
assert changed == [target]
new_archive = b''.join(chunks)
new_archive += b'\0' * (-len(new_archive) % 512)
new = {name: (fields, payload) for name, fields, payload, _, _ in entries(new_archive)}
assert old.keys() == new.keys()
for name in old:
    if name != target:
        assert old[name] == new[name], name
ramdisk = out / 'ramdisk.cpio.gz'
ramdisk.write_bytes(gzip.compress(new_archive, mtime=0))
image = out / 'aura-kali-v25-power-recovery.img'
manifest = json.loads((root / 'build/kali/boot-manifest-v25.json').read_text())
subprocess.run([sys.executable, str(root / 'sources/mkbootimg/mkbootimg.py'),
               '--kernel', str(out / 'original/kernel'), '--ramdisk', str(ramdisk),
               '--header_version', '1', '--pagesize', '4096', '--base', '0',
               '--kernel_offset', '32768', '--ramdisk_offset', '16777216', '--tags_offset', '256',
               '--os_version', '9.0.0', '--os_patch_level', '2020-11',
               '--cmdline', manifest['cmdline'], '--output', str(image)], check=True)
assert image.stat().st_size < 67108864
with image.open('ab') as stream:
    stream.write(b'\0' * (67108864-image.stat().st_size))
subprocess.run([sys.executable, str(root / 'sources/mkbootimg/unpack_bootimg.py'),
               '--boot_img', str(image), '--out', str(out / 'roundtrip')], check=True, stdout=subprocess.DEVNULL)
assert (out / 'roundtrip/kernel').read_bytes() == (out / 'original/kernel').read_bytes()
assert (out / 'roundtrip/ramdisk').read_bytes() == ramdisk.read_bytes()
record = {'base': 'v25', 'changed_entries': changed,
          'kernel_and_device_tree_unchanged': True, 'other_ramdisk_entries_unchanged': True,
          'image': str(image.relative_to(root)), 'bytes': image.stat().st_size,
          'sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
          'guard_sha256': hashlib.sha256(replacement).hexdigest(),
          'validation': '16 shell policy tests; boot image roundtrip; all other ramdisk entries match v25',
          'phone_installed': False}
(out / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
