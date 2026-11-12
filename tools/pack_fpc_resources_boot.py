"""Add only fingerprint GPIO nodes to the verified v26 DT. Run under WSL."""
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

root = Path(__file__).resolve().parents[1]
out = root / 'build/kali/fpc-resources-test'
out.mkdir(exist_ok=True)
base = root / 'build/kali/qseecom-test/aura-kali-v26-qseecom.img'
assert hashlib.sha256(base.read_bytes()).hexdigest() == '09c0bdb8cfeb35c0d175aee94d9414c61ae6865ac5cfc72ec70eb7c4052e076a'
subprocess.run([sys.executable, str(root/'sources/mkbootimg/unpack_bootimg.py'), '--boot_img', str(base), '--out', str(out/'base')], check=True, stdout=subprocess.DEVNULL)
combined = (out/'base/kernel').read_bytes()
split = zlib.decompressobj(31)
split.decompress(combined)
dtb = split.unused_data
kernel = combined[:-len(dtb)]
(out/'base.dtb').write_bytes(dtb)

def nodes(data):
    magic, total, pos, strings = struct.unpack_from('>4I', data)
    assert magic == 0xd00dfeed and total == len(data)
    stack, result = [], {}
    while True:
        token = struct.unpack_from('>I', data, pos)[0]; pos += 4
        if token == 1:
            end = data.index(0, pos)
            stack.append(data[pos:end].decode()); pos = (end+4)&~3
            result['/'+'/'.join(stack[1:])] = {}
        elif token == 2:
            stack.pop()
        elif token == 3:
            size, name = struct.unpack_from('>II', data, pos); pos += 8
            start = strings + name
            result['/'+'/'.join(stack[1:])][data[start:data.index(0,start)].decode()] = data[pos:pos+size]
            pos = (pos+size+3)&~3
        elif token == 9:
            return result
        else:
            assert token == 4

before = nodes(dtb)
tlmm = [path for path, props in before.items() if props.get('compatible') == b'qcom,sdm845-pinctrl\0']
assert len(tlmm) == 1
tlmm = tlmm[0]
phandle = struct.unpack('>I', before[tlmm]['phandle'])[0]
overlay = '''/dts-v1/;
/plugin/;
/ {
    fragment@0 {
        target-path = "/";
        __overlay__ {
            fingerprint {
                compatible = "razer,aura-fpc-resources";
                reset-gpios = <TLMM 95 1>;
                irq-gpios = <TLMM 121 0>;
                pinctrl-names = "default";
                pinctrl-0 = <&fpc_reset &fpc_irq>;
                status = "okay";
            };
        };
    };
    fragment@1 {
        target-path = "TLMM_PATH";
        __overlay__ {
            fpc_reset: fingerprint-reset-state {
                pins = "gpio95";
                function = "gpio";
                drive-strength = <2>;
                bias-disable;
            };
            fpc_irq: fingerprint-irq-state {
                pins = "gpio121";
                function = "gpio";
                drive-strength = <2>;
                bias-pull-up;
                input-enable;
            };
        };
    };
};
'''.replace('TLMM_PATH', tlmm).replace('TLMM', hex(phandle))
(out/'resources.dtso').write_text(overlay)
subprocess.run(['dtc', '-I', 'dts', '-O', 'dtb', '-o', str(out/'resources.dtbo'), str(out/'resources.dtso')], check=True)
subprocess.run(['fdtoverlay', '-i', str(out/'base.dtb'), '-o', str(out/'resources.dtb'), str(out/'resources.dtbo')], check=True)
new_dtb = (out/'resources.dtb').read_bytes()
after = nodes(new_dtb)
assert all(after.get(path) == props for path, props in before.items()), 'Existing DT property changed'
added = set(after)-set(before)
assert added == {'/fingerprint', tlmm+'/fingerprint-reset-state', tlmm+'/fingerprint-irq-state'}, added
assert after['/fingerprint']['reset-gpios'] == struct.pack('>3I', phandle, 95, 1)
assert after['/fingerprint']['irq-gpios'] == struct.pack('>3I', phandle, 121, 0)
(out/'kernel-dtb').write_bytes(kernel+new_dtb)
image = out/'aura-kali-v26-fpc-resources.img'
cmdline = json.loads((root/'build/kali/boot-manifest-v25.json').read_text())['cmdline']
subprocess.run([sys.executable, str(root/'sources/mkbootimg/mkbootimg.py'), '--kernel', str(out/'kernel-dtb'), '--ramdisk', str(out/'base/ramdisk'), '--header_version', '1', '--pagesize', '4096', '--base', '0', '--kernel_offset', '32768', '--ramdisk_offset', '16777216', '--tags_offset', '256', '--os_version', '9.0.0', '--os_patch_level', '2020-11', '--cmdline', cmdline, '--output', str(image)], check=True)
assert image.stat().st_size < 67108864
with image.open('ab') as f:
    f.write(b'\0'*(67108864-image.stat().st_size))
subprocess.run([sys.executable, str(root/'sources/mkbootimg/unpack_bootimg.py'), '--boot_img', str(image), '--out', str(out/'roundtrip')], check=True, stdout=subprocess.DEVNULL)
assert (out/'roundtrip/kernel').read_bytes() == kernel+new_dtb
assert (out/'roundtrip/ramdisk').read_bytes() == (out/'base/ramdisk').read_bytes()
image.with_suffix('.img.gz').write_bytes(gzip.compress(image.read_bytes(), mtime=0))
manifest = {'image': str(image.relative_to(root)), 'sha256': hashlib.sha256(image.read_bytes()).hexdigest(), 'base_sha256': hashlib.sha256(base.read_bytes()).hexdigest(), 'kernel_unchanged': True, 'ramdisk_unchanged': True, 'existing_dt_properties_unchanged': True, 'added_nodes': sorted(added), 'automatic_reset': False, 'phone_installed': False}
(out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps(manifest, indent=2))
