"""Explicit phases for the first headless aura mainline test and restoration."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import run_diagnostic_test as transport

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/mainline'
CAPTURE=ROOT/'device-data/20261006-181410-429985'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('phase',choices=['validate','flash','start','restore'])
parser.add_argument('--version',choices=['v1','v2','v3','v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11'],default='v3')
args=parser.parse_args()
transport.RUN=ROOT/('test-runs/mainline-'+args.version)
image_name='aura-mainline-diag-'+args.version+'.img'
command=transport.command


def backups():
    manifest=json.loads((CAPTURE/'manifest.json').read_text())
    for name in ('boot_a','boot_b','dtbo_a','dtbo_b','vbmeta_a','vbmeta_b'):
        data=(CAPTURE/(name+'.img')).read_bytes()
        record=manifest['files'][name+'.img']
        assert record['phone_sha256_verified'] and len(data)==record['bytes']
        assert hashlib.sha256(data).hexdigest()==record['sha256']


def validate():
    backups()
    manifest=json.loads((BUILD/'image-manifest.json').read_text())
    assert manifest.get('diagnostic_version','v1')==args.version
    assert manifest['source_revision']=='a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0'
    for name,record in manifest['files'].items():
        assert Path(name).name==name
        data=(BUILD/name).read_bytes()
        assert len(data)==record['bytes'] and hashlib.sha256(data).hexdigest()==record['sha256']
    assert (BUILD/image_name).stat().st_size==67108864
    assert (BUILD/'blank-dtbo.img').read_bytes()==b'\0'*8388608
    assert (BUILD/'roundtrip/kernel').read_bytes()==(BUILD/'Image.gz-dtb').read_bytes()
    assert (BUILD/'roundtrip/ramdisk').read_bytes()==(BUILD/'initramfs.cpio.gz').read_bytes()
    transport.save('validated-manifest',manifest)
    print('Kernel image, unpack roundtrip, blank inactive DTBO, and six original recovery backups verified.',flush=True)


def restore():
    backups()
    assert 'product: cheryl2' in command('restore-product','getvar','product')
    command('restore-active-a','set_active','a')
    assert 'current-slot: a' in command('restore-slot','getvar','current-slot')
    command('restore-original-boot-b','flash','boot_b',str(CAPTURE/'boot_b.img'))
    command('restore-original-dtbo-b','flash','dtbo_b',str(CAPTURE/'dtbo_b.img'))
    command('reboot-original-android','reboot')


phase=args.phase
if phase=='validate':
    validate()
elif phase=='flash':
    validate()
    assert 'product: cheryl2' in command('product','getvar','product')
    assert 'current-slot: a' in command('slot-before','getvar','current-slot')
    assert 'unlocked: yes' in command('unlocked','getvar','unlocked')
    assert '0x4000000' in command('boot-b-size','getvar','partition-size:boot_b')
    assert '0x800000' in command('dtbo-b-size','getvar','partition-size:dtbo_b')
    command('flash-mainline-boot-b','flash','boot_b',str(BUILD/image_name))
    command('flash-blank-dtbo-b','flash','dtbo_b',str(BUILD/'blank-dtbo.img'))
elif phase=='start':
    for name in ('flash-mainline-boot-b','flash-blank-dtbo-b'):
        assert json.loads((transport.RUN/(name+'.json')).read_text())['code']==0
    assert 'current-slot: a' in command('slot-before-start','getvar','current-slot')
    command('activate-b','set_active','b')
    assert 'current-slot: b' in command('slot-test','getvar','current-slot')
    command('reboot-mainline','reboot')
elif phase=='restore':
    restore()
