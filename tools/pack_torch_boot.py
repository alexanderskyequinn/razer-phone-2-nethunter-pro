"""Package torch board wiring with the verified v16 kernel and no automatic light."""
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
candidate = out/'torch-kernel'
candidate.mkdir(exist_ok=True)
shutil.copyfile(kernel, candidate/'Image.gz')
shutil.copyfile(root/'build/mainline/sdm845-razer-aura.dtb', candidate/'sdm845-razer-aura.dtb')
subprocess.run([sys.executable, str(root/'tools/pack_kali_boot.py'), '--version', 'v17', '--kernel-dir', str(candidate)], check=True)
manifest = json.loads((out/'boot-manifest-v17.json').read_text())
old = 'cb171a68f0ba4b52d232f11dbc46419f5051eb990e7c4c5c53f64eb31df16f0c'
new = manifest['files']['aura-kali-trial-v17.img']['sha256']
installer = (root/'diagnostic/kali-install-boot-v16.sh').read_text()
installer = installer.replace('old=037dccf410bf48e018cac2c744501073ce01389a3d17ffbf1f9318bcef25c77b', 'old='+old)
installer = installer.replace('new='+old, 'new='+new)
installer = installer.replace('aura-kali-trial-v16.img', 'aura-kali-trial-v17.img').replace('boot-v15-before-wireless-reporting.img', 'boot-v16-before-torch.img').replace('wireless-reporting-before-reboot', 'torch-before-reboot').replace('v16 boot image', 'v17 boot image').replace('v15 backup', 'v16 backup')
assert 'old='+old in installer and 'new='+new in installer
(root/'diagnostic/kali-install-boot-v17.sh').write_bytes(installer.encode())
report = {'status':'Built; not installed or hardware tested.', 'boot_version':'v17', 'boot':manifest['files']['aura-kali-trial-v17.img'], 'module_sha256':hashlib.sha256((out/'torch/leds-aura-lm3644.ko').read_bytes()).hexdigest(), 'scope':'CCI0 bus and 1.8 V LVS1 regulator; same v16 kernel. Separate LM3644 torch module exposes 32 levels capped below89 mA per LED; no flash mode; LEDs off at boot.', 'references':['sources/razer-kernel-reference/arch/arm64/boot/dts/qcom/fih/rc2/flashled-lm3644.dtsi','https://www.ti.com/lit/ds/symlink/lm3644.pdf'], 'rollback':'/var/lib/aura/boot-v16-before-torch.img'}
(out/'torch-progress.json').write_text(json.dumps(report,indent=2)+'\n')
