"""Bundle logo modules; keep the known working kernel and boot image intact."""
import hashlib,io,json,shutil,subprocess,sys,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]; out=root/'build/kali'
old=out/'v12-logo-baseline'
subprocess.run([sys.executable,str(root/'sources/mkbootimg/unpack_bootimg.py'),'--boot_img',str(out/'aura-kali-trial-v12.img'),'--out',str(old)],check=True,stdout=subprocess.DEVNULL)
kernel=(root/'build/mainline-display-fix/Image.gz').read_bytes()
assert (old/'kernel').read_bytes().startswith(kernel),'Current build kernel differs from working v12'
(old/'board.dtb').write_bytes((old/'kernel').read_bytes()[len(kernel):])
candidate=out/'logo-kernel'
candidate.mkdir(exist_ok=True)
(candidate/'Image.gz').write_bytes(kernel)
shutil.copyfile(root/'build/mainline/sdm845-razer-aura.dtb',candidate/'sdm845-razer-aura.dtb')
subprocess.run([sys.executable,str(root/'tools/pack_kali_boot.py'),'--version','v14','--kernel-dir',str(candidate)],check=True)
release=(root/'build/mainline/kernel-release.txt').read_text().strip()
assert release=='6.18.2-aura-bringup1+'
hashes={}
with tarfile.open(out/'logo-modules.tar','w') as tar:
 for name in ['leds-lp55xx-common.ko','leds-lp5523.ko']:
  data=(out/'logo-modules'/name).read_bytes()
  dest=f'lib/modules/{release}/updates/aura/{name}'
  info=tarfile.TarInfo(dest);info.size=len(data);info.mode=0o644;info.uname=info.gname='root'
  tar.addfile(info,io.BytesIO(data));hashes[dest]=hashlib.sha256(data).hexdigest()
report={'kernel_unchanged_from_v12':True,'files':hashes,'archive_sha256':hashlib.sha256((out/'logo-modules.tar').read_bytes()).hexdigest(),'boot_image':json.loads((out/'boot-manifest-v14.json').read_text())['files']['aura-kali-trial-v14.img'],'status':'Built; physical logo test pending','limits':'9 individual channels at stock8mA; max current capped8mA, off at startup. Color/channel mapping and power use pending.'}
(out/'logo-progress.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
