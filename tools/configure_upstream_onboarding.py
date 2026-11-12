"""Install upstream Phosh First Boot + packaged Phrog into the clean release."""
from pathlib import Path
import json,os,shutil,subprocess
project=Path(__file__).resolve().parents[1]
root=Path('/var/tmp/aura-kali-release-rootfs')
source=project/'sources/phosh-first-boot'
binaries=project/'build/kali/upstream-onboarding'
assert root.resolve()==root and os.getuid()==0
def remove(rel):
    p=root/rel
    assert '..' not in p.parts
    if p.is_symlink() or p.is_file():p.unlink()
    elif p.is_dir():shutil.rmtree(p)
def write(rel,text,mode=0o644):
    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
    if p.is_symlink():p.unlink()
    p.write_text(text.replace('\r\n','\n'));p.chmod(mode)
def link(rel,target):
    remove(rel);p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.symlink_to(target)
for name,target in [('phosh-first-boot','usr/bin/phosh-first-boot'),('phosh-first-boot-importer','usr/libexec/phosh-first-boot-importer')]:
    shutil.copy2(binaries/name,root/target);(root/target).chmod(0o755)
# Remove the prototype UI, privilege service and temporary unlock exceptions.
for rel in ('usr/local/bin/aura-setup-app','usr/local/libexec/aura-setup-service',
            'usr/local/libexec/aura-phosh-shell-start','etc/systemd/system/aura-setup.service',
            'etc/systemd/system/multi-user.target.wants/aura-setup.service',
            'etc/xdg/autostart/org.aura.Setup.desktop','etc/dconf/db/local.d/90-aura-setup',
            'etc/systemd/user/mobi.phosh.Shell.service.d/90-aura-setup.conf',
            'etc/systemd/system/phosh.service.d/90-aura-initialize.conf','var/lib/aura/setup-complete'):
    remove(rel)
if subprocess.run(['chroot',str(root),'id','kali'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
    subprocess.run(['chroot',str(root),'userdel','kali'],check=True)
remove('home/kali')
for rel in ('etc/shadow-','etc/gshadow-','etc/passwd-','etc/group-'):remove(rel)
remove('var/lib/greetd')
greeter=next(line.split(':') for line in (root/'etc/passwd').read_text().splitlines() if line.startswith('_greetd:'))
home=root/greeter[5].lstrip('/');home.mkdir(parents=True,exist_ok=True)
os.chown(home,int(greeter[2]),int(greeter[3]));home.chmod(0o700)
defaults=(source/'data/defaults.conf').read_text()
# Only supported distro configuration; keep upstream PIN/user handling intact.
defaults=defaults.replace('"video",','"video", "render", "audio", "input",')
write('usr/share/phosh-first-boot/defaults.conf',defaults)
write('usr/share/glib-2.0/schemas/mobi.phosh.FirstBoot.gschema.xml',(source/'data/mobi.phosh.FirstBoot.gschema.xml').read_text())
write('usr/share/glib-2.0/schemas/00_mobi.phosh.FirstBoot.gschema.override',
      (source/'data/00_mobi.phosh.FirstBoot.gschema.override.in').read_text().replace('@bindir@','/usr/bin'))
write('usr/share/polkit-1/rules.d/20-phosh-first-boot.rules',
      (source/'data/20-phosh-first-boot.rules.in').read_text().replace('@setup_user@','_greetd'))
write('usr/lib/tmpfiles.d/phosh-first-boot.conf',
      (source/'data/tmpfiles/phosh-first-boot.conf.in').read_text().replace('@dir@','/run/phosh-first-boot').replace('@user@','_greetd').replace('@group@','_greetd'))
write('usr/lib/systemd/user/phosh-first-boot-importer.service',
      (source/'data/phosh-first-boot-importer.service.in').read_text().replace('@libexecdir@','/usr/libexec'))
link('etc/systemd/user/graphical-session.target.wants/phosh-first-boot-importer.service','/usr/lib/systemd/user/phosh-first-boot-importer.service')
for icon in (source/'data/icons').rglob('*.svg'):
    rel=icon.relative_to(source/'data/icons')
    if 'symbolic' in str(rel):target='usr/share/icons/hicolor/symbolic/apps/mobi.phosh.FirstBoot-symbolic.svg'
    else:target='usr/share/icons/hicolor/scalable/apps/mobi.phosh.FirstBoot.svg'
    write(target,icon.read_text())
for locale in ('de','pl'):
    mo=root/f'usr/share/locale/{locale}/LC_MESSAGES/phosh-first-boot.mo'
    mo.parent.mkdir(parents=True,exist_ok=True)
    result=subprocess.run(['chroot','/var/tmp/aura-kali-rootfs','msgfmt','-o','-','-'],
                          input=(source/'po'/f'{locale}.po').read_bytes(),capture_output=True,check=True)
    mo.write_bytes(result.stdout)
# Use the distribution's login manager and its stock first-run mechanism.
remove('etc/systemd/system/greetd.service')
for rel in ('etc/systemd/system/graphical.target.wants/phosh.service',):remove(rel)
link('etc/systemd/system/phosh.service','/dev/null')
link('etc/systemd/system/display-manager.service','/usr/lib/systemd/system/greetd.service')
write('etc/systemd/system/greetd.service.d/90-aura-initialize.conf',
      '[Unit]\nRequires=aura-initialize.service\nAfter=aura-initialize.service\n')
for unit in ('systemd-homed.service','systemd-userdbd.socket'):
    directory='sockets.target.wants' if unit.endswith('.socket') else 'multi-user.target.wants'
    link('etc/systemd/system/'+directory+'/'+unit,'/usr/lib/systemd/system/'+unit)
# Keep the tested display compositor in the normal desktop session.
desktop=root/'usr/share/wayland-sessions/phosh.desktop'
desktop.write_text(desktop.read_text().replace('Exec=phosh-session','Exec=/usr/local/libexec/aura-phosh-crossfade-session'))
write('etc/environment','PHOC_AURA_ROTATION_CROSSFADE=1\n')
write('etc/aura-onboarding','phosh-first-boot 0.2.0\nphrog 0.53.0-2\n')
# Private enrollments are empty; retain engineering UI only as a hidden fallback
# until a production fingerprint backend is connected to fprintd.
for p in (root/'usr/share/applications').glob('*[Ff]ingerprint*'):
    if 'aura' in p.name.lower():
        p.write_text(p.read_text()+'\nNoDisplay=true\n')
subprocess.run(['chroot',str(root),'glib-compile-schemas','/usr/share/glib-2.0/schemas'],check=True)
subprocess.run(['chroot',str(root),'dconf','update'],check=True)
subprocess.run(['chroot',str(root),'ldconfig'],check=True)
# Discard only package installation state in this offline staging tree.
for rel in ('var/tmp','var/log','var/cache/apt/archives'):
    remove(rel);(root/rel).mkdir(parents=True,exist_ok=True)
(root/'var/tmp').chmod(0o1777)
packages=subprocess.check_output(['chroot',str(root),'dpkg-query','-W'],text=True)
(project/'build/kali/release/packages.txt').write_text(packages)
report={'provider':'phosh-first-boot','version':'0.2.0','commit':'9c69b23ff4029d48efd6dcd0b9d6287dbc12d9d8',
        'greeter':'phrog','custom_setup_ui_shipped':False,'source_behavior_patches':False,
        'account_backend':'systemd-homed','home_storage':'luks','hardware_first_boot_tested':False}
(project/'build/kali/release/onboarding.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
