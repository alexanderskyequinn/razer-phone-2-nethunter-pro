from pathlib import Path
import gzip,json,subprocess,sys
root=Path(__file__).resolve().parents[1]
out=root/'build/kali'
pack=root/'tools/pack_kali_boot.py'
text=pack.read_text()
if "'v24'" not in text: pack.write_bytes(text.replace("'v23'", "'v23', 'v24'").encode())
subprocess.run([sys.executable,str(pack),'--version','v24','--kernel-dir',str(out/'telefocus')],check=True)
def sha(v): return json.loads((out/f'boot-manifest-v{v}.json').read_text())['files'][f'aura-kali-trial-v{v}.img']['sha256']
old,new=sha(23),sha(24)
s=(root/'diagnostic/kali-install-boot-v23.sh').read_text().replace('old='+sha(22),'old='+old).replace('new='+old,'new='+new)
s=s.replace('aura-kali-trial-v23.img','aura-kali-trial-v24.img').replace('boot-v22-before-telecamera.img','boot-v23-before-telefocus.img').replace('v23 boot image','v24 boot image').replace('v22 backup','v23 backup')
(root/'diagnostic/kali-install-boot-v24.sh').write_bytes(s.encode())
s=(root/'diagnostic/kali-telecamera-update-launch.sh').read_text().replace('v23','v24').replace(old,new).replace('telecamera','telefocus')
(root/'diagnostic/kali-telefocus-update-launch.sh').write_bytes(s.encode())
with gzip.GzipFile(out/'aura-kali-trial-v24.img.gz','wb',mtime=0) as f:f.write((out/'aura-kali-trial-v24.img').read_bytes())
print(new)
