from pathlib import Path
import gzip, json, subprocess, sys
root = Path(__file__).resolve().parents[1]
out = root/'build/kali'
pack = root/'tools/pack_kali_boot.py'
text = pack.read_text()
if "'v23'" not in text:
    pack.write_bytes(text.replace("'v22'", "'v22', 'v23'").encode())
subprocess.run([sys.executable, str(pack), '--version', 'v23', '--kernel-dir', str(out/'telecamera')], check=True)
old = json.loads((out/'boot-manifest-v22.json').read_text())['files']['aura-kali-trial-v22.img']['sha256']
new = json.loads((out/'boot-manifest-v23.json').read_text())['files']['aura-kali-trial-v23.img']['sha256']
previous = json.loads((out/'boot-manifest-v21.json').read_text())['files']['aura-kali-trial-v21.img']['sha256']
s = (root/'diagnostic/kali-install-boot-v22.sh').read_text()
s = s.replace('old='+previous, 'old='+old).replace('new='+old, 'new='+new)
s = s.replace('aura-kali-trial-v22.img', 'aura-kali-trial-v23.img').replace('boot-v21-before-camera-busfix.img','boot-v22-before-telecamera.img')
s = s.replace('v22 boot image','v23 boot image').replace('v21 backup','v22 backup')
(root/'diagnostic/kali-install-boot-v23.sh').write_bytes(s.encode())
s = (root/'diagnostic/kali-camera-busfix-update-launch.sh').read_text().replace('v22','v23').replace(old,new).replace('camera-busfix','telecamera')
(root/'diagnostic/kali-telecamera-update-launch.sh').write_bytes(s.encode())
with gzip.GzipFile(out/'aura-kali-trial-v23.img.gz', 'wb', mtime=0) as f:
    f.write((out/'aura-kali-trial-v23.img').read_bytes())
print(new)
