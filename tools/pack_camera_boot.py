"""Package rear camera wiring using the verified v17 kernel, with v17 rollback."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
out = root/'build/kali'
kernel = root/'build/mainline-wireless-reporting/Image.gz'
assert hashlib.sha256(kernel.read_bytes()).hexdigest() == '1e1ffd4d00abd25bfaf9256c6a77d9bb6f6e8240e2928677c09421f27d0799a6'
candidate = out/'camera-kernel'
candidate.mkdir(exist_ok=True)
shutil.copyfile(kernel, candidate/'Image.gz')
shutil.copyfile(root/'build/mainline/sdm845-razer-aura.dtb', candidate/'sdm845-razer-aura.dtb')
subprocess.run([sys.executable, str(root/'tools/pack_kali_boot.py'), '--version', 'v18', '--kernel-dir', str(candidate)], check=True)
manifest = json.loads((out/'boot-manifest-v18.json').read_text())
old = '1076f83f3e7f6d066b192c2c129028ddb614bc28bb20042ea2319cde29eb7aa5'
new = manifest['files']['aura-kali-trial-v18.img']['sha256']
installer = (root/'diagnostic/kali-install-boot-v17.sh').read_text()
installer = installer.replace('new='+old, 'new='+new)
installer = installer.replace('old=cb171a68f0ba4b52d232f11dbc46419f5051eb990e7c4c5c53f64eb31df16f0c', 'old='+old)
installer = installer.replace('aura-kali-trial-v17.img', 'aura-kali-trial-v18.img').replace('boot-v16-before-torch.img', 'boot-v17-before-camera.img').replace('torch-before-reboot', 'camera-before-reboot').replace('v17 boot image', 'v18 boot image').replace('v16 backup', 'v17 backup')
assert 'old='+old in installer and 'new='+new in installer
(root/'diagnostic/kali-install-boot-v18.sh').write_bytes(installer.encode())
module_hash = hashlib.sha256((out/'camera/imx363.ko').read_bytes()).hexdigest()
launcher = (root/'diagnostic/kali-launch-torch-update.sh').read_text()
launcher = launcher.replace('leds-aura-lm3644.ko', 'imx363.ko').replace('50d9112cf95c6ade4853b87292aff852a9a219aff4c38d2c625b8225303dfd46', module_hash).replace('v17.sh','v18.sh').replace('torch-update','camera-update')
(root/'diagnostic/kali-launch-camera-update.sh').write_bytes(launcher.encode())
report = {'status':'Built; sensor detection not yet tested', 'boot_version':'v18', 'boot':manifest['files']['aura-kali-trial-v18.img'], 'module_sha256':module_hash, 'rollback':'/var/lib/aura/boot-v17-before-camera.img', 'scope':'Main rear Sony IMX363 on CCI0/CSI0; stock Razer PMIC GPIO10/11/12 enables, reset80, MCLK0. Telephoto/front/focus/OIS remain unconfigured.'}
(out/'camera-progress.json').write_text(json.dumps(report,indent=2)+'\n')
