from pathlib import Path
import json,subprocess,sys,gzip
root=Path(__file__).resolve().parents[1]
out=root/'build/kali'
pack=root/'tools/pack_kali_boot.py'
text=pack.read_text()
if "'v22'" not in text:pack.write_bytes(text.replace("'v21'", "'v21', 'v22'").encode())
subprocess.run([sys.executable,str(pack),'--version','v22','--kernel-dir',str(out/'camera-probe')],check=True)
old=json.loads((out/'boot-manifest-v21.json').read_text())['files']['aura-kali-trial-v21.img']['sha256']
new=json.loads((out/'boot-manifest-v22.json').read_text())['files']['aura-kali-trial-v22.img']['sha256']
old20='3b7dd3eb53a8ca2fe3fda39380c61152975bdb785eb7a09fb4f7312d6478c59c'
s=(root/'diagnostic/kali-install-boot-v21.sh').read_text().replace('old='+old20,'old='+old).replace('new='+old,'new='+new)
s=s.replace('aura-kali-trial-v21.img','aura-kali-trial-v22.img').replace('boot-v20-before-camera-probe.img','boot-v21-before-camera-busfix.img').replace('v21 boot image','v22 boot image').replace('v20 backup','v21 backup')
(root/'diagnostic/kali-install-boot-v22.sh').write_bytes(s.encode())
s=(root/'diagnostic/kali-camera-probe-update-launch.sh').read_text().replace('v21','v22').replace(old,new).replace('aura-camera-probe-update','aura-camera-busfix-update').replace('camera-probe-update.log','camera-busfix-update.log')
(root/'diagnostic/kali-camera-busfix-update-launch.sh').write_bytes(s.encode())
with gzip.GzipFile(out/'aura-kali-trial-v22.img.gz','wb',mtime=0) as f:f.write((out/'aura-kali-trial-v22.img').read_bytes())
print(new)
