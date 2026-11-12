"""Fail closed if a clean staging tree contains development identities or access."""
from pathlib import Path
import hashlib,json,os,re,subprocess
project=Path(__file__).resolve().parents[1]
root=Path('/var/tmp/aura-kali-release-rootfs')
out=project/'build/kali/release'
issues=[]
def require(ok,message):
    if not ok:issues.append(message)
require((root/'etc/machine-id').read_bytes()==b'','machine-id not empty')
require(not (root/'etc/aura-install-id').exists(),'personal install ID')
for folder in ('root','home','etc/NetworkManager/system-connections','var/lib/bluetooth','var/tmp'):
    p=root/folder
    require(not p.exists() or not any(p.iterdir()),'Nonempty personal-state directory: '+folder)
for line in (root/'etc/shadow').read_text().splitlines():
    name,password,*_=line.split(':')
    require(password in ('!','*','!!','!*'),'Usable initial account credential: '+name)
for unit in ('ssh.service','ssh.socket','aura-wifi-ssh.service','aura-usb-gadget.service','aura-usb-dhcp.service'):
    p=root/'etc/systemd/system'/unit
    require(p.is_symlink() and os.readlink(p)=='/dev/null','Remote service not masked: '+unit)
public=(project/'device-data/kali-access/id_ed25519.pub').read_text().split()[1].encode()
needles=[public,b'REPLACE_WITH_YOUR_INSTALL_ID',b'YOUR_DEVICE_SERIAL',b'192.0.2.78']
matches=[]
for prefix in ('etc','usr/local','opt','var/lib','root','home'):
    for p in (root/prefix).rglob('*'):
        if p.is_symlink() or not p.is_file():continue
        if p.name in ('authorized_keys','authorized_keys2') or p.name.startswith('ssh_host_'):
            issues.append('Saved SSH credentials: '+str(p.relative_to(root)))
        if p.stat().st_size > 64*1024*1024:continue
        data=p.read_bytes()
        if any(n in data for n in needles):matches.append(str(p.relative_to(root)))
require(not matches,'Development identifiers found: '+repr(matches))
result=subprocess.run(['chroot',str(root),'dpkg','--audit'],capture_output=True,text=True)
require(result.returncode==0 and not result.stdout.strip(),'Package audit failed: '+result.stdout)
dependencies={}
for path in ('usr/local/libexec/aura-phoc-crossfade','usr/local/libexec/aura-iio-sensor-proxy',
             'usr/local/libexec/aura-fpc-bio','usr/local/libexec/aura-qsee-rpmb-authenticated',
             'opt/aura-camera/lib/libcamera.so.0.7.2','usr/bin/snapshot','usr/bin/nautilus',
             'usr/bin/phosh-first-boot','usr/libexec/phosh-first-boot-importer','usr/bin/phrog'):
    require((root/path).is_file(),'Missing required runtime: '+path)
    if not (root/path).is_file():continue
    elf=subprocess.check_output(['aarch64-linux-gnu-readelf','-l',str(root/path)],text=True)
    dynamic='INTERP' in elf or path.endswith('.so.0.7.2')
    code=None
    if dynamic:
        r=subprocess.run(['chroot',str(root),'/lib/ld-linux-aarch64.so.1','--list','/'+path],capture_output=True,text=True)
        code=r.returncode
        require(code==0,'Missing runtime dependency for '+path+': '+r.stderr)
    dependencies[path]={'dynamic':dynamic,'check_exit':code}
require(not any(line.startswith('kali:') for line in (root/'etc/passwd').read_text().splitlines()),'Development account remains')
for path in ('usr/local/bin/aura-setup-app','usr/local/libexec/aura-setup-service','etc/dconf/db/local.d/90-aura-setup'):
    require(not (root/path).exists(),'Custom first-run prototype remains: '+path)
require((root/'etc/aura-onboarding').read_text().startswith('phosh-first-boot '),'Missing upstream onboarding')
require(os.readlink(root/'etc/systemd/system/display-manager.service')=='/usr/lib/systemd/system/greetd.service','Wrong login manager')
first_run=subprocess.run(['chroot',str(root),'env','XDG_CURRENT_DESKTOP=Phrog:Phosh:GNOME',
                         'GSETTINGS_BACKEND=memory','gsettings','get','mobi.phosh.phrog','first-run'],capture_output=True,text=True)
require(first_run.returncode==0 and first_run.stdout.strip()=="'/usr/bin/phosh-first-boot'",'Greeter does not launch upstream first-run setup')
require('systemd' in next(line for line in (root/'etc/nsswitch.conf').read_text().splitlines() if line.startswith('passwd:')),
        'Homed account lookup unavailable')
report={'passed':not issues,'issues':issues,'personal_identifier_matches':matches,'dependencies':dependencies,
        'first_run_provider':'phosh-first-boot','setup_not_completed':not any((root/'home').iterdir()),
        'greeter_first_run_command':first_run.stdout.strip(),
        'redistribution_ready':False,'redistribution_remaining':['Vendor firmware licensing and source-offer review','Fresh-install hardware acceptance']}
(out/'privacy-and-runtime-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(bool(issues))
