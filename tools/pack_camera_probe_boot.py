from pathlib import Path
import json,subprocess,sys,gzip
root=Path(__file__).resolve().parents[1]
out=root/'build/kali'
pack=root/'tools/pack_kali_boot.py'
text=pack.read_text()
if "'v21'" not in text:
    pack.write_bytes(text.replace("'v20'", "'v20', 'v21'").encode())
subprocess.run([sys.executable,str(pack),'--version','v21','--kernel-dir',str(out/'camera-probe')],check=True)
manifest=json.loads((out/'boot-manifest-v21.json').read_text())
old='3b7dd3eb53a8ca2fe3fda39380c61152975bdb785eb7a09fb4f7312d6478c59c'
new=manifest['files']['aura-kali-trial-v21.img']['sha256']
installer=(root/'diagnostic/kali-install-boot-v20.sh').read_text().replace('old=985deb8f7761969b558cfdbb1025cc363173dedfe57bb24d7844919b984dc951','old='+old).replace('new='+old,'new='+new)
installer=installer.replace('aura-kali-trial-v20.img','aura-kali-trial-v21.img').replace('boot-v19-before-panel-wake.img','boot-v20-before-camera-probe.img').replace('panel-wake-before-reboot','camera-probe-before-reboot').replace('v20 boot image','v21 boot image').replace('v19 backup','v20 backup')
assert 'old='+old in installer and 'new='+new in installer
(root/'diagnostic/kali-install-boot-v21.sh').write_bytes(installer.encode())
launch=(root/'diagnostic/kali-panel-wake-update-launch.sh').read_text().replace('v20','v21').replace(old,new).replace('aura-panel-wake-update','aura-camera-probe-update').replace('panel-wake-update.log','camera-probe-update.log')
(root/'diagnostic/kali-camera-probe-update-launch.sh').write_bytes(launch.encode())
with gzip.GzipFile(out/'aura-kali-trial-v21.img.gz','wb',mtime=0) as f:f.write((out/'aura-kali-trial-v21.img').read_bytes())
(out/'camera-probe-progress.json').write_text(json.dumps({'installed':False,'version':'v21','status':'Built one-shot sensor identification candidate; driver not auto-loaded. No sensor programming or calibration writes.','boot':manifest['files']['aura-kali-trial-v21.img'],'rollback':'/var/lib/aura/boot-v20-before-camera-probe.img','expected_sensors':{'imx351':'CCI1 address0x1a ID0x0351 at0x0016','s5k3h7':'CCI1 address0x2d ID0x3087 at0x0000'}},indent=2)+'\n')
print(new)
