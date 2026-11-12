"""Enable receiver bus access with the verified v14 kernel, without charging writes."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'build/kali'
old=out/'v14-wireless-baseline'
assert hashlib.sha256((out/'aura-kali-trial-v14.img').read_bytes()).hexdigest() == 'b06fa26b6b35eb06a0ea62eca9fabbbd00a16136e6ec2b669bc55894c590be6c'
subprocess.run([sys.executable,str(root/'sources/mkbootimg/unpack_bootimg.py'),'--boot_img',str(out/'aura-kali-trial-v14.img'),'--out',str(old)],check=True,stdout=subprocess.DEVNULL)
kernel=(root/'build/mainline-display-fix/Image.gz').read_bytes()
assert (old/'kernel').read_bytes().startswith(kernel)
(old/'board.dtb').write_bytes((old/'kernel').read_bytes()[len(kernel):])
candidate=out/'wireless-probe-kernel';candidate.mkdir(exist_ok=True)
(candidate/'Image.gz').write_bytes(kernel)
shutil.copyfile(root/'build/mainline/sdm845-razer-aura.dtb',candidate/'sdm845-razer-aura.dtb')
subprocess.run([sys.executable,str(root/'tools/pack_kali_boot.py'),'--version','v15','--kernel-dir',str(candidate)],check=True)
report={'status':'Built; not installed. First step is receiver identification only.','scope':'Enable SE7 I2C bus; no receiver register, GPIO enable, firmware, FOD, voltage or charge current change. Includes already-installed Logo Light app overlay.','kernel':'Exact kernel bytes from verified v14.','boot':json.loads((out/'boot-manifest-v15.json').read_text())['files']['aura-kali-trial-v15.img'],'references':['sources/razer-kernel-reference/arch/arm64/boot/dts/qcom/fih/rc2/wireless-charging-P9221.dtsi','sources/razer-kernel-reference/drivers/power/supply/p9221_wl_charger.c','sources/charger-upstream/manifest.json']}
(out/'wireless-progress.json').write_text(json.dumps(report,indent=2)+'\n')
