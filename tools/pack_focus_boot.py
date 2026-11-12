"""Package v19 focus wiring, preserving the verified v18 rollback."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
out=root/'build/kali'
pack=root/'tools/pack_kali_boot.py'
text=pack.read_text()
if "'v19'" not in text:
    pack.write_bytes(text.replace("'v18'", "'v18', 'v19'").encode())
kernel=root/'build/mainline-wireless-reporting/Image.gz'
assert hashlib.sha256(kernel.read_bytes()).hexdigest()=='1e1ffd4d00abd25bfaf9256c6a77d9bb6f6e8240e2928677c09421f27d0799a6'
candidate=out/'focus-kernel'
candidate.mkdir(exist_ok=True)
shutil.copyfile(kernel,candidate/'Image.gz')
shutil.copyfile(root/'build/mainline/sdm845-razer-aura.dtb',candidate/'sdm845-razer-aura.dtb')
subprocess.run([sys.executable,str(pack),'--version','v19','--kernel-dir',str(candidate)],check=True)
manifest=json.loads((out/'boot-manifest-v19.json').read_text())
old='f7824f9506b100ab17a9a72b1a3e0e78bfd9b0a01650c87b2b5e9d461ae68580'
new=manifest['files']['aura-kali-trial-v19.img']['sha256']
installer=(root/'diagnostic/kali-install-boot-v18.sh').read_text()
installer=installer.replace('old=1076f83f3e7f6d066b192c2c129028ddb614bc28bb20042ea2319cde29eb7aa5','old='+old).replace('new='+old,'new='+new)
installer=installer.replace('aura-kali-trial-v18.img','aura-kali-trial-v19.img').replace('boot-v17-before-camera.img','boot-v18-before-focus.img').replace('camera-before-reboot','focus-before-reboot').replace('v18 boot image','v19 boot image').replace('v17 backup','v18 backup')
assert 'old='+old in installer and 'new='+new in installer
(root/'diagnostic/kali-install-boot-v19.sh').write_bytes(installer.encode())
module=hashlib.sha256((out/'focus/bu64753.ko').read_bytes()).hexdigest()
(out/'focus-progress.json').write_text(json.dumps({'installed':False,'boot_version':'v19','boot':manifest['files']['aura-kali-trial-v19.img'],'module_sha256':module,'status':'Built, hardware probe pending','rollback':'/var/lib/aura/boot-v18-before-focus.img','stock_reference':'device-data/camera-reference/imx363-tables.json; stock ARM Thumb focus routine 0x237320, direct DAC shift at0x2373d2; initial50, tuned range50..800'},indent=2)+'\n')
