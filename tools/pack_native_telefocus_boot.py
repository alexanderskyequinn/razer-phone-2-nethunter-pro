from pathlib import Path
import gzip,json,subprocess,sys
root=Path(__file__).resolve().parents[1]
out=root/'build/kali'
pack=root/'tools/pack_kali_boot.py'
text=pack.read_text()
if "'v25'" not in text: pack.write_bytes(text.replace("'v24'", "'v24', 'v25'").encode())
subprocess.run([sys.executable,str(pack),'--version','v25','--kernel-dir',str(out/'native-telefocus')],check=True)
def sha(v): return json.loads((out/f'boot-manifest-v{v}.json').read_text())['files'][f'aura-kali-trial-v{v}.img']['sha256']
old,new=sha(24),sha(25)
s=(root/'diagnostic/kali-install-boot-v24.sh').read_text().replace('old='+sha(23),'old='+old).replace('new='+old,'new='+new)
s=s.replace('aura-kali-trial-v24.img','aura-kali-trial-v25.img').replace('boot-v23-before-telefocus.img','boot-v24-before-native-telefocus.img').replace('v24 boot image','v25 boot image').replace('v23 backup','v24 backup')
assert 'old='+old in s and 'new='+new in s
s=s.replace('dd if="$image" of="$boot"', '''echo '268587665456a82baded5f7dd8e9402ad66c6f0793a9e83aad3464eea4cc8bee  /var/lib/aura/lc898217xc.ko' | sha256sum -c -
test "$(uname -r)" = '6.18.2-aura-bringup1+'
install -m 0644 /var/lib/aura/lc898217xc.ko /lib/modules/6.18.2-aura-bringup1+/updates/aura/lc898217xc.ko
depmod -a
dd if="$image" of="$boot"''')
(root/'diagnostic/kali-install-boot-v25.sh').write_bytes(s.encode())
s=(root/'diagnostic/kali-telefocus-update-launch.sh').read_text().replace('v24','v25').replace(old,new).replace('telefocus','native-telefocus')
(root/'diagnostic/kali-native-telefocus-update-launch.sh').write_bytes(s.encode())
with gzip.GzipFile(out/'aura-kali-trial-v25.img.gz','wb',mtime=0) as f:f.write((out/'aura-kali-trial-v25.img').read_bytes())
print(new)
