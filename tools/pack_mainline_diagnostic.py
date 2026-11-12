"""Package an experimental RAM-only kernel test; no device operations."""
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
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', choices=['v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11'], default='v3')
version = parser.parse_args().version
OUT = ROOT/'build/mainline'
DIAG = ROOT/'build/diagnostic'
kernel = (OUT/'Image.gz').read_bytes()
raw = gzip.decompress(kernel)
assert raw[56:60] == b'ARM\x64'
dtb = (OUT/'sdm845-razer-aura.dtb').read_bytes()
assert dtb[:4] == b'\xd0\x0d\xfe\xed'
assert struct.unpack_from('>I',dtb,4)[0] == len(dtb)
init = (ROOT/'diagnostic/mainline-init').read_bytes().replace(b'\r\n',b'\n')
assert ('AURA_MAINLINE_DIAG_' + version.upper()).encode() in init
entries = [(n,b'',0o040755,(0,0)) for n in ('bin','dev','proc','sys','run','www','config')]
entries += [('bin/busybox',(DIAG/'busybox').read_bytes(),0o100755,(0,0)),
            ('bin/return-to-bootloader',(DIAG/'return-to-bootloader').read_bytes(),0o100755,(0,0)),
            ('bin/sh',b'busybox',0o120777,(0,0)),('init',init,0o100755,(0,0)),
            ('report-template.img.gz',(DIAG/'report-template.img.gz').read_bytes(),0o100644,(0,0)),
            ('dev/console',b'',0o020600,(5,1)),('dev/null',b'',0o020666,(1,3))]
if version in ('v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11'):
    entries.append(('bin/probe-storage',(ROOT/'diagnostic/probe-storage').read_bytes().replace(b'\r\n',b'\n'),0o100755,(0,0)))
if version == 'v5':
    entries += [('bin/probe-touch',(ROOT/'diagnostic/probe-touch').read_bytes().replace(b'\r\n',b'\n'),0o100755,(0,0)),
                ('bin/read-touch',(OUT/'read-touch').read_bytes(),0o100755,(0,0))]
if version in ('v6', 'v7', 'v8', 'v9', 'v10', 'v11'):
    entries.append(('bin/display-pattern',(OUT/'display-pattern').read_bytes(),0o100755,(0,0)))
cpio=b''.join(archive_entry(n,p,m,i,d) for i,(n,p,m,d) in enumerate(entries,1))+archive_entry('TRAILER!!!')
cpio+=b'\0'*(-len(cpio)%512)
(OUT/'initramfs.cpio.gz').write_bytes(gzip.compress(cpio,mtime=0))
(OUT/'Image.gz-dtb').write_bytes(kernel+dtb)
cmdline='earlycon console=ttyMSM0,115200n8 rdinit=/init loglevel=8 ignore_loglevel printk.devkmsg=on clk_ignore_unused pd_ignore_unused regulator_ignore_unused fw_devlink=permissive panic=10'
if version == 'v11':
    for flag in ('clk_ignore_unused ', 'pd_ignore_unused ', 'regulator_ignore_unused '):
        cmdline = cmdline.replace(flag, '')
image=OUT/f'aura-mainline-diag-{version}.img'
subprocess.run([sys.executable,str(ROOT/'sources/mkbootimg/mkbootimg.py'),
    '--kernel',str(OUT/'Image.gz-dtb'),'--ramdisk',str(OUT/'initramfs.cpio.gz'),
    '--header_version','1','--pagesize','4096','--base','0',
    '--kernel_offset','32768','--ramdisk_offset','16777216','--tags_offset','256',
    '--os_version','9.0.0','--os_patch_level','2020-11','--cmdline',cmdline,'--output',str(image)],check=True)
assert image.stat().st_size < 67108864
with image.open('ab') as f: f.write(b'\0'*(67108864-image.stat().st_size))
(OUT/'blank-dtbo.img').write_bytes(b'\0'*8388608)
report={'status':'UNTESTED EXPERIMENTAL KERNEL DIAGNOSTIC',
        'diagnostic_version':version,
        'source_revision':'a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0',
        'kernel_version':'6.18.2-aura-bringup1', 'cmdline':cmdline,
        'files':{str(p.relative_to(OUT)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in (image,OUT/'Image.gz',OUT/'sdm845-razer-aura.dtb',OUT/'initramfs.cpio.gz',OUT/'blank-dtbo.img')},
        'init_sha256':hashlib.sha256(init).hexdigest(),
        'test_scope':'RAM-only hardware test through boot_b with blank dtbo_b. Experimental boot_b/dtbo_b may remain installed per user instruction. Android slot A untouched.',
        'unvalidated':['bootloader DT selection','USB2 transfer','reset-to-bootloader','power/thermal','display','storage','charging','all peripherals']}
(OUT/'image-manifest.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
