"""Build a separate RAM-only ARM64 recovery from pinned kernel and local packages.

Run as root in WSL. Default builds contain no login keys or network services.
Development SSH requires an explicitly supplied public key.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

p = argparse.ArgumentParser()
p.add_argument('--test-seconds', type=int, default=0)
p.add_argument('--authorized-key', type=Path, help='Explicit opt-in development SSH public key; omitted for portable recovery')
p.add_argument('--output-dir', type=Path)
args = p.parse_args()
assert args.test_seconds == 0 or 120 <= args.test_seconds <= 1800
project = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-kali-rootfs')
out = args.output_dir or project / 'build/kali/rescue'
out.mkdir(parents=True, exist_ok=True)
work = Path(tempfile.mkdtemp(prefix='aura-rescue-', dir='/var/tmp'))
tree = work / 'root'
tree.mkdir()
assert os.geteuid() == 0

def run(*cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)

def write(path, text, mode=0o644):
    dest = tree / path.lstrip('/')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text.replace('\r\n', '\n'))
    dest.chmod(mode)

def put(src, path, mode=0o755):
    dest = tree / path.lstrip('/')
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    dest.chmod(mode)

seen = set()
def elf(src, path):
    if path in seen:
        return
    seen.add(path)
    put(src, path)
    info = run('aarch64-linux-gnu-readelf', '-l', '-d', str(src), capture_output=True, text=True).stdout
    names = re.findall(r'Shared library: \[([^\]]+)\]', info)
    interp = re.search(r'Requesting program interpreter: ([^\]]+)', info)
    if interp:
        name = interp[1]
        elf(source / name.lstrip('/'), name)
    for name in names:
        candidates = [source / folder / name for folder in ('usr/lib/aarch64-linux-gnu', 'lib/aarch64-linux-gnu', 'usr/lib', 'lib')]
        dep = next((f for f in candidates if f.is_file()), None)
        if dep is None:
            raise RuntimeError('Missing ARM64 dependency: ' + name)
        elf(dep, '/lib/aarch64-linux-gnu/' + name)

for d in ('dev','proc','sys','run/sshd','tmp','root/.ssh','etc/ssh','mnt','var/empty'):
    (tree/d).mkdir(parents=True, exist_ok=True)
(tree/'root').chmod(0o700)
(tree/'root/.ssh').chmod(0o700)
(tree/'tmp').chmod(0o1777)
for name, minor in (('null',3),('random',8),('urandom',9)):
    os.mknod(tree/'dev'/name, stat.S_IFCHR | 0o666, os.makedev(1,minor))
put(project/'build/diagnostic/busybox', '/bin/busybox')
(tree/'bin/sh').symlink_to('busybox')
put(project/'build/diagnostic/return-to-bootloader', '/bin/return-to-bootloader')
run('aarch64-linux-gnu-gcc', '-static', '-Os', '-Wall', '-Wextra', '-Werror',
    str(project/'port/aura-rescue/screen.c'), '-o', str(work/'aura-rescue-screen'))
put(work/'aura-rescue-screen', '/bin/aura-rescue-screen')
# Use the regression-tested correction; upstream assigns the active GUID to A
# even when B is selected, which makes this bootloader unable to load images.
put(project/'build/kali/rescue/qbootctl-fixed', '/usr/bin/qbootctl')
executables = ['/usr/sbin/e2fsck','/usr/sbin/resize2fs','/usr/sbin/tune2fs']
if args.authorized_key:
    executables += ['/usr/sbin/sshd','/usr/bin/ssh-keygen','/usr/lib/openssh/sshd-session',
                    '/usr/lib/openssh/sshd-auth','/usr/lib/openssh/sftp-server']
for path in executables:
    elf(source/path.lstrip('/'), path)
for name in ('init', 'aura-rescue', 'aura-rescue-power'):
    write('/init' if name == 'init' else '/bin/'+name, (project/'port/aura-rescue'/name).read_text(), 0o755)
usb = (project/'port/kali-overlay/usr/local/sbin/aura-usb-gadget').read_text()
usb = usb.replace('/usr/local/libexec/busybox', '/bin/busybox').replace('Kali NetHunter Pro - Razer Phone 2','Aura RAM Recovery')
usb += '\n/bin/busybox udhcpd /run/aura-udhcpd.conf\n'
write('/bin/aura-rescue-usb', usb, 0o755)
if args.authorized_key:
    public = args.authorized_key.read_text().strip().split()
    assert len(public) >= 2 and public[0] == 'ssh-ed25519'
    write('/root/.ssh/authorized_keys', ' '.join(public[:2])+'\n', 0o600)
    run('ssh-keygen', '-l', '-f', str(tree/'root/.ssh/authorized_keys'), stdout=subprocess.DEVNULL)
    write('/etc/aura-rescue-remote-enabled', 'Explicit development build\n')
write('/etc/passwd', 'root:x:0:0:Recovery:/root:/bin/sh\nsshd:x:74:74:SSH:/var/empty:/bin/false\n')
write('/etc/shadow', 'root::0:0:99999:7:::\nsshd:!:0:0:99999:7:::\n', 0o600)
write('/etc/group', 'root:x:0:\nsshd:x:74:\n')
write('/etc/nsswitch.conf', 'passwd: files\ngroup: files\nshadow: files\nhosts: files\n')
write('/etc/hosts', '127.0.0.1 localhost\n192.0.2.1 aura-recovery\n')
write('/etc/aura-rescue-version', 'Aura RAM Recovery v1\n')
write('/etc/ssh/sshd_config', '''Port 22
ListenAddress 192.0.2.1
ListenAddress 169.254.84.5
HostKey /run/ssh_host_ed25519_key
PidFile /run/sshd.pid
UsePAM no
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitEmptyPasswords no
AuthenticationMethods publickey
AuthorizedKeysFile .ssh/authorized_keys
AllowUsers root
DisableForwarding yes
UseDNS no
Subsystem sftp /usr/lib/openssh/sftp-server
''')
if args.test_seconds:
    write('/etc/aura-rescue-test-seconds', str(args.test_seconds)+'\n')
# Validate interpreter, tools and ssh config entirely in the isolated tree.
run('chroot', str(tree), '/bin/busybox', '--install', '-s', '/bin')
for name in ('init','bin/aura-rescue','bin/aura-rescue-power','bin/aura-rescue-usb'):
    run('sh', '-n', str(tree/name))
run('chroot', str(tree), '/usr/sbin/e2fsck', '-V')
# Generate disposable validation keys only for opt-in development builds.
if args.authorized_key:
    run('ssh-keygen','-q','-t','ed25519','-N','','-f',str(tree/'run/ssh_host_ed25519_key'))
    run('chroot',str(tree),'/usr/sbin/sshd','-t','-f','/etc/ssh/sshd_config')
    for f in (tree/'run').glob('ssh_host*'):
        f.unlink()
else:
    assert not (tree/'root/.ssh/authorized_keys').exists()
    assert not (tree/'usr/sbin/sshd').exists()
base = project/'build/kali/fpc-resources-test/aura-kali-v26-fpc-resources.img'
assert hashlib.sha256(base.read_bytes()).hexdigest() == '2fdfb649c979f70ebc44c82c9d33c9a7580e2f67e2e798b5f9567a8396cd8abd'
run(sys.executable,str(project/'sources/mkbootimg/unpack_bootimg.py'),'--boot_img',str(base),'--out',str(work/'boot'),stdout=subprocess.DEVNULL)
listing = b'\0'.join(str(f.relative_to(tree)).encode() for f in sorted(tree.rglob('*'))) + b'\0'
archive = run('cpio','--null','-o','--format=newc','--owner=0:0',input=listing,cwd=tree,capture_output=True).stdout
ramdisk = out/'rescue.cpio.gz'
ramdisk.write_bytes(gzip.compress(archive,mtime=0))
image = out/'aura-recovery-v1.img'
run(sys.executable,str(project/'sources/mkbootimg/mkbootimg.py'),'--kernel',str(work/'boot/kernel'),
    '--ramdisk',str(ramdisk),'--header_version','1','--pagesize','4096','--base','0',
    '--kernel_offset','32768','--ramdisk_offset','16777216','--tags_offset','256',
    '--os_version','9.0.0','--os_patch_level','2020-11',
    '--cmdline','console=tty0 rdinit=/init loglevel=3 fw_devlink=permissive panic=10 systemd.gpt_auto=0 systemd.repart=0',
    '--output',str(image))
assert image.stat().st_size < 67108864
with image.open('ab') as f:
    f.write(b'\0'*(67108864-image.stat().st_size))
run(sys.executable,str(project/'sources/mkbootimg/unpack_bootimg.py'),'--boot_img',str(image),'--out',str(work/'verify'),stdout=subprocess.DEVNULL)
assert (work/'verify/kernel').read_bytes() == (work/'boot/kernel').read_bytes()
assert (work/'verify/ramdisk').read_bytes() == ramdisk.read_bytes()
image.with_suffix('.img.gz').write_bytes(gzip.compress(image.read_bytes(),mtime=0))
manifest = {'image':str(image.relative_to(project)), 'sha256':hashlib.sha256(image.read_bytes()).hexdigest(),
            'qbootctl_sha256':hashlib.sha256((tree/'usr/bin/qbootctl').read_bytes()).hexdigest(),
            'kernel_unchanged':True,'ram_only':True,'automatic_mounts':False,'public_key_personalized':bool(args.authorized_key),
            'remote_access_enabled':bool(args.authorized_key),
            'contains_private_keys':False,'test_timeout_seconds':args.test_seconds,'hardware_tested':False,
            'build_tree':str(tree),'runtime_files':sorted(seen)}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({k:v for k,v in manifest.items() if k!='runtime_files'},indent=2))
