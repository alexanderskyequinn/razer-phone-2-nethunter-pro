"""Install missing packaged dependencies inside the release-only chroot."""
from pathlib import Path
import argparse, json, os, shutil, subprocess
parser=argparse.ArgumentParser()
parser.add_argument('--onboarding-build',action='store_true')
parser.add_argument('--onboarding-runtime',action='store_true')
parser.add_argument('--apps',action='store_true',help='Install the user-selected standard apps and full Kali toolkit')
options=parser.parse_args()
project=Path(__file__).resolve().parents[1]
root=Path('/var/tmp/aura-kali-release-rootfs')
if options.onboarding_build: root=Path('/var/tmp/aura-kali-rootfs')
assert root.resolve()==root and os.getuid()==0
gap=json.loads((project/'build/kali/release/package-gap.json').read_text())
cache=root/'var/tmp/release-debs'
cache.mkdir(parents=True,exist_ok=True)
args=[]
for name,path in ({} if options.onboarding_build or options.onboarding_runtime or options.apps else gap['cached']).items():
    dest=cache/Path(path).name
    shutil.copy2(path,dest)
    args.append('/var/tmp/release-debs/'+dest.name)
policy=root/'usr/sbin/policy-rc.d'
policy.write_text('#!/bin/sh\nexit 101\n'); policy.chmod(0o755)
resolver=root/'etc/resolv.conf'
resolver.unlink(missing_ok=True)
resolver.write_text(Path('/etc/resolv.conf').read_text())
mounts=[]
try:
    for directory in ('proc','dev','run'):
        (root/directory).mkdir(exist_ok=True)
        typ='proc' if directory=='proc' else 'tmpfs'
        subprocess.run(['mount','-t',typ,typ,str(root/directory)],check=True)
        mounts.append(root/directory)
    import stat
    for name,minor in [('null',3),('zero',5),('random',8),('urandom',9)]:
        os.mknod(root/'dev'/name,stat.S_IFCHR|0o666,os.makedev(1,minor))
    env=dict(os.environ,DEBIAN_FRONTEND='noninteractive')
    command=['chroot',str(root),'apt-get','install','-y','--no-install-recommends']
    packages=['qbootctl=0.2.2-1+b1','libturbojpeg0','gstreamer1.0-tools']
    if options.onboarding_build: packages=['libpms-dev','libadwaita-1-dev','libgtk-4-dev','libcrypt-dev','gettext']
    if options.onboarding_runtime: packages=['phrog','libpms-1.0-0','systemd-homed','phosh-mobile-settings','fprintd']
    if options.apps:
        selection=json.loads((project/'port/app-packages.json').read_text())
        packages=selection['everyday']+selection['kali']+selection['media_support']
        command.remove('--no-install-recommends')
    subprocess.run(command+args+packages,check=True,env=env)
    if options.apps:
        subprocess.run(['chroot',str(root),'systemctl','disable','smartmontools.service'],check=True)
finally:
    for path in reversed(mounts): subprocess.run(['umount',str(path)],check=True)
    policy.unlink(missing_ok=True)
    resolver.unlink(missing_ok=True);resolver.symlink_to('/run/NetworkManager/resolv.conf')
print('Release dependency installation complete.')
