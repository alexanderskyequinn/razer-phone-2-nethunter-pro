"""Save a reproducible patch relative to the existing aura 6.18.2 source."""
import difflib
import hashlib
import json
from pathlib import Path
import shutil

project = Path(__file__).resolve().parents[1]
before = Path('/var/tmp/aura-mainline-6.18.2/linux')
after = Path('/var/tmp/aura-qseecom-6.18.2/linux')
files = json.loads((project / 'sources/qseecom-reference/compare.json').read_text())['files']
patch = []
for item in files:
    name = item['filename']
    a, b = before / name, after / name
    patch.extend(difflib.unified_diff(a.read_text().splitlines(True) if a.exists() else [],
                                   b.read_text().splitlines(True),
                                   fromfile='a/' + name if a.exists() else '/dev/null',
                                   tofile='b/' + name))
dest = project / 'port/qseecom-tee-6.18.2-experimental.patch'
dest.write_text(''.join(patch))
target = project / 'build/kali/fingerprint-resources'
objects = []
for name in ('drivers/tee/qseecom/core.o', 'drivers/firmware/qcom/qcom_scm.o',
             'drivers/soc/qcom/mdt_loader.o'):
    src = after.parent / 'out' / name
    dst = target / (name.replace('/', '-'))
    shutil.copyfile(src, dst)
    objects.append({'source': name, 'file': dst.name,
                    'sha256': hashlib.sha256(dst.read_bytes()).hexdigest()})
record = {'status': 'Compile-only; not installed or runtime validated',
          'reference_commit': '662435b853d865d360507f5daee6ff309838c5ca',
          'reference_url': 'https://github.com/wrobelda/linux/tree/662435b853d865d360507f5daee6ff309838c5ca',
          'kernel': '6.18.2-aura-bringup1+',
          'patch_sha256': hashlib.sha256(dest.read_bytes()).hexdigest(),
          'objects': objects,
          'validation': 'ARM64 compiler W=1 for modified objects; final Image.gz built and linked successfully',
          'changes': ['32-bit cmnlib service-image startup using stock SCM command 0x07',
                      'Boot-lifetime cmnlib success cache in SCM; no automatic firmware load at probe',
                      'Serialize named-app lookup/load and registry publication',
                      'Keep session alive throughout invocation; release app reference after failed session allocation',
                      'Handle tee_shm_get_from_id error pointers correctly'],
          'remaining': ['Live cmnlib and TA load verification with physical recovery available',
                        'Listener service and FPC sensor protocol integration',
                        'Real sensor identity, capture, enrollment and desktop integration']}
image = after.parent / 'out/arch/arm64/boot/Image.gz'
image_target = target / 'Image-qseecom-experimental.gz'
shutil.copyfile(image, image_target)
record['image'] = {'file': image_target.name,
                   'sha256': hashlib.sha256(image_target.read_bytes()).hexdigest(),
                   'installed': False,
                   'build_log': 'test-runs/snapshot/fingerprint-kernel-final-link.txt'}
record['build_warnings'] = 'Initial full build reported six unused-variable warnings in two unrelated panel drivers; no fingerprint build warnings'
(target / 'qseecom-build.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
