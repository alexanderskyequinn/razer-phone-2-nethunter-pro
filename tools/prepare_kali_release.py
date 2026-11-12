"""Assemble an isolated clean release tree from offline packages and audited code.

Run inside WSL as root. Never reads the live phone, and never modifies a disk.
Vendor firmware remains a separate, local-only input pending redistribution review.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

PROJECT = Path(__file__).resolve().parents[1]
ROOT = Path('/var/tmp/aura-kali-release-rootfs')
OUT = PROJECT/'build/kali/release'
assert os.getuid() == 0 and ROOT.is_dir() and ROOT.resolve() == ROOT
assert not any(x == str(ROOT) or x.startswith(str(ROOT)+'/') for x in subprocess.check_output(['findmnt','-rn','-o','TARGET'],text=True).splitlines())

def run(*args, **kw):
    return subprocess.run(args, check=True, **kw)

def remove(rel):
    p = ROOT/rel
    assert str(p).startswith(str(ROOT)+'/') and '..' not in p.parts
    if p.is_symlink() or p.is_file(): p.unlink()
    elif p.is_dir(): shutil.rmtree(p)

def write(rel, data, mode=0o644):
    p = ROOT/rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_symlink(): p.unlink()
    p.write_text(data.replace('\r\n','\n'))
    p.chmod(mode)

def link(rel,target):
    remove(rel)
    p=ROOT/rel
    p.parent.mkdir(parents=True,exist_ok=True)
    p.symlink_to(target)

archive = OUT/'aura-release-runtime.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '445fba08030cc9412475f1f95ab8a3705bfa7786f73a1d6916f825e93423e157'
manifest = json.loads((OUT/'aura-release-runtime-manifest.json').read_text())
with tarfile.open(archive) as tar:
    members=tar.getmembers()
    assert {m.name for m in members} == set(manifest)
    for m in members:
        assert not m.name.startswith('/') and '..' not in Path(m.name).parts
        assert not m.name.startswith(('home/','root/','var/'))
        # Existing absolute links belong to the staged root, never the host.
        destination=ROOT/m.name
        if destination.is_symlink(): destination.unlink()
        if m.isfile():
            assert hashlib.sha256(tar.extractfile(m).read()).hexdigest() == manifest[m.name]['sha256']
        elif m.issym():
            assert m.linkname == manifest[m.name]['symlink']
            if m.linkname.startswith('/'):
                m.linkname=os.path.relpath(ROOT/m.linkname.lstrip('/'),(ROOT/m.name).parent)
            if m.name in ('usr/lib/firmware/regulatory.db','usr/lib/firmware/regulatory.db.p7s'):
                m.linkname=Path(m.name).name+'-debian'
        else: raise RuntimeError('Unexpected archive member '+m.name)
    tar.extractall(ROOT,members=members,filter='data')

# Destroy only known staging-tree state; source tree and phone stay untouched.
for rel in ('home/kali','root','var/lib/aura','var/lib/NetworkManager','var/lib/bluetooth',
            'var/lib/systemd/random-seed','var/lib/AccountsService/users','var/lib/AccountsService/icons',
            'var/lib/sss','var/cache','var/log','var/tmp','tmp','run','mnt','etc/NetworkManager/system-connections',
            'etc/aura','etc/aura-install-id','etc/aura-wifi-ssh-profile','etc/aura-recovery.sha256',
            'etc/ssh/sshd_config.d/10-aura-development.conf','etc/systemd/system/ssh.service.d',
            'etc/systemd/system/aura-wifi-ssh.service','etc/NetworkManager/dispatcher.d/90-aura-wifi-ssh'):
    remove(rel)
for key in (ROOT/'etc/ssh').glob('ssh_host_*'): key.unlink()
for rel in ('root','var/cache','var/log','tmp','run','etc/NetworkManager/system-connections'):
    (ROOT/rel).mkdir(parents=True,exist_ok=True)
(ROOT/'root').chmod(0o700)
(ROOT/'tmp').chmod(0o1777)
if subprocess.run(['chroot',str(ROOT),'id','kali'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode == 0:
    run('chroot',str(ROOT),'userdel','kali')
run('chroot',str(ROOT),'usermod','--password','!','root')
# Delete shadow backups as well, rather than retain the development PIN hash.
for rel in ('etc/shadow-','etc/gshadow-','etc/passwd-','etc/group-'):
    remove(rel)
write('etc/machine-id','')
remove('var/lib/dbus/machine-id')
link('var/lib/dbus/machine-id','/etc/machine-id')
write('etc/hostname','kali-aura\n')
write('etc/hosts','127.0.0.1 localhost\n127.0.1.1 kali-aura\n::1 localhost\n')
write('etc/fstab','# Native root is mounted by the Aura initramfs.\n')
write('etc/aura-release','AURA_NATIVE_RELEASE=1\nDEVICE=razer,aura\n')
write('etc/dconf/db/local.d/91-aura-release',"[org/gnome/desktop/session]\nidle-delay=uint32 120\n")
write('etc/dconf/db/local.d/92-aura-apps',"[sm/puri/phosh]\napp-filter-mode=[]\n")
remove('etc/systemd/system/multi-user.target.wants/smartmontools.service')
camera_userspace=PROJECT/'build/kali/camera/aura-libcamera-focus-timing-trial.tar.gz'
assert hashlib.sha256(camera_userspace.read_bytes()).hexdigest() == '6f546d39f543f6b2089e50d1a4054d4690c21485693f7fb47e70dd22bb118897'
with tarfile.open(camera_userspace) as tar:
    assert all(m.name == 'opt' or m.name.startswith('opt/aura-camera/') or m.name == 'opt/aura-camera' for m in tar.getmembers())
    tar.extractall(ROOT,filter='data')
camera=PROJECT/'build/kali/camera-startup/imx363.ko'
assert hashlib.sha256(camera.read_bytes()).hexdigest()=='5a426de89a882eb2de9d7b87abc0d76e203b20e4b85a42acd8c068ff2a44a424'
shutil.copy2(camera,ROOT/'usr/lib/modules/6.18.2-aura-bringup1+/updates/aura/imx363.ko')

src=PROJECT/'port/aura-setup'
for name,target in [('aura-initialize','usr/local/libexec/aura-initialize')]:
    data=(src/name).read_text()
    write(target,data,0o755)
    ast.parse(data)
for name in ('aura-initialize.service',):
    write('etc/systemd/system/'+name,(src/name).read_text())
    link('etc/systemd/system/multi-user.target.wants/'+name,'/etc/systemd/system/'+name)
write('etc/systemd/system/aura-first-boot-guard.service.d/20-persistent.conf',
      (PROJECT/'port/kali-overlay/etc/systemd/system/aura-first-boot-guard.service.d/20-persistent.conf').read_text())
# Remote entry points remain masked until the owner explicitly configures them.
for unit in ('ssh.service','ssh.socket','aura-wifi-ssh.service','regenerate-ssh-host-keys.service',
             'aura-display-power.service','aura-usb-gadget.service','aura-usb-dhcp.service'):
    for wants in (ROOT/'etc/systemd/system').glob('*.wants'):
        (wants/unit).unlink(missing_ok=True)
    link('etc/systemd/system/'+unit,'/dev/null')
for name in ('aura-cpu-boost.service','aura-first-boot-guard.service','aura-bluetooth-address.service',
             'qrtr-ns.service','pd-mapper.service','rmtfs.service','tqftpserv.service','qbootctl.service'):
    system='/etc/systemd/system/'+name
    target=system if (ROOT/system.lstrip('/')).is_file() else '/usr/lib/systemd/system/'+name
    assert (ROOT/target.lstrip('/')).is_file(),target
    link('etc/systemd/system/multi-user.target.wants/'+name,target)
link('etc/systemd/system/default.target.wants/hexagonrpcd.service','/usr/lib/systemd/system/hexagonrpcd.service')
link('etc/systemd/system/default.target','/usr/lib/systemd/system/graphical.target')
link('etc/systemd/system/graphical.target.wants/phosh.service','/usr/lib/systemd/system/phosh.service')
link('etc/systemd/system/sleep.target.wants/aura-bluetooth-sleep.service','/etc/systemd/system/aura-bluetooth-sleep.service')
# Use a device marker, not this development installation's UUID, for app checks.
helper=ROOT/'usr/local/libexec/aura-fingerprint-helper'
text=helper.read_text()
old="Path('/etc/aura-install-id').read_text().strip() != 'REPLACE_WITH_YOUR_INSTALL_ID'"
assert text.count(old)==1
helper.write_text(text.replace(old,"'AURA_NATIVE_RELEASE=1' not in Path('/etc/aura-release').read_text().splitlines()"))
helper.chmod(0o755)
recovery=json.loads((OUT/'recovery/manifest.json').read_text())
assert not recovery['remote_access_enabled'] and not recovery['public_key_personalized']
write('etc/aura-recovery.sha256',recovery['sha256']+'  /dev/disk/by-partlabel/boot_a\n'+
      '2daeb1f36095b44b318410b3f4e8b5d989dcc7bb023d1426c492dab0a3053e74  /dev/disk/by-partlabel/dtbo_a\n'+
      recovery['qbootctl_sha256']+'  /usr/local/libexec/aura-qbootctl\n')
run('depmod','-b',str(ROOT),'6.18.2-aura-bringup1+')
run('chroot',str(ROOT),'dconf','update')
run('chroot',str(ROOT),'ldconfig')
run('chroot',str(ROOT),'update-desktop-database','/usr/share/applications')
audit=run('chroot',str(ROOT),'dpkg','--audit',capture_output=True,text=True).stdout
assert not audit.strip(),audit
packages=run('chroot',str(ROOT),'dpkg-query','-W',capture_output=True,text=True).stdout
(OUT/'packages.txt').write_text(packages)
print('Clean staging configured; run privacy, dependency and first-run tests before imaging.')
run('python3',str(PROJECT/'tools/configure_upstream_onboarding.py'))
