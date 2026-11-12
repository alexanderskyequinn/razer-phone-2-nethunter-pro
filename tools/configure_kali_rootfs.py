"""Configure the local ARM64 Kali filesystem. Run in WSL as root after packages."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import uuid

TEST_PIN = os.environ.get('AURA_TEST_PIN', '')
if not (TEST_PIN.isascii() and TEST_PIN.isdigit() and 6 <= len(TEST_PIN) <= 64):
    raise SystemExit('Set AURA_TEST_PIN to your own 6-64 digit development PIN')

PROJECT = Path(__file__).resolve().parents[1]
ROOT = Path('/var/tmp/aura-kali-rootfs')
STATE = Path('/var/tmp/aura-kali-build/resume-state')
OUT = PROJECT / 'build/kali'
assert os.geteuid() == 0 and ROOT.resolve() == ROOT
assert (STATE / 'desktop.done').exists() and (STATE / 'nethunter.done').exists()
OUT.mkdir(parents=True, exist_ok=True)

def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)

def chroot(*args, **kwargs):
    return run('chroot', str(ROOT), *args, **kwargs)

def write(name, text, mode=0o644):
    path = ROOT / name.lstrip('/')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(mode)

def link(name, target):
    path = ROOT / name.lstrip('/')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    path.symlink_to(target)

identity_path = OUT / 'identity.json'
if not identity_path.exists():
    identity_path.write_text(json.dumps({'root_uuid': str(uuid.uuid4()), 'install_id': str(uuid.uuid4())}, indent=2))
identity = json.loads(identity_path.read_text())
write('/etc/aura-install-id', identity['install_id'] + '\n')
write('/etc/hostname', 'kali-aura\n')
write('/etc/hosts', '127.0.0.1 localhost\n127.0.1.1 kali-aura\n::1 localhost ip6-localhost ip6-loopback\n')
write('/etc/fstab', '# First trial: immutable userdata filesystem with RAM overlay.\n')

for src in (PROJECT / 'port/kali-overlay').rglob('*'):
    if src.is_file():
        rel = src.relative_to(PROJECT / 'port/kali-overlay')
        write(str(rel), src.read_text(), 0o755 if rel.as_posix().startswith(('usr/local/sbin/', 'usr/local/bin/', 'etc/NetworkManager/dispatcher.d/')) else 0o644)
wifi_access = OUT / 'wifi-access.json'
if wifi_access.exists():
    wifi = json.loads(wifi_access.read_text())
    if wifi.get('installed') and wifi.get('install_id') == identity['install_id']:
        write('/etc/aura-wifi-ssh-profile', str(uuid.UUID(wifi['profile_uuid'])) + '\n', 0o600)
        link('/etc/systemd/system/multi-user.target.wants/aura-wifi-ssh.service', '/etc/systemd/system/aura-wifi-ssh.service')
for src, name in [('busybox', 'busybox'), ('return-to-bootloader', 'aura-return-to-bootloader')]:
    dst = ROOT / 'usr/local/libexec' / name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PROJECT / 'build/diagnostic' / src, dst)
    dst.chmod(0o755)

# Keep the validated rotation compositor separate from the packaged binary.
assert subprocess.check_output(['chroot', str(ROOT), 'dpkg-query', '-W', '-f=${Version}', 'phoc'], text=True).strip() == '0.58~alpha1-1', 'Rebuild rotation compositor against the updated Phoc package'
crossfade = OUT / 'phoc-crossfade/phoc'
assert hashlib.sha256(crossfade.read_bytes()).hexdigest() == '12c47e799a482fed557a8d671f9cd2b959fadcd19c9fc71a87d95a855486b35d'
shutil.copyfile(crossfade, ROOT / 'usr/local/libexec/aura-phoc-crossfade')
(ROOT / 'usr/local/libexec/aura-phoc-crossfade').chmod(0o755)
write('/usr/local/libexec/aura-phosh-crossfade-session', (ROOT / 'usr/bin/phosh-session').read_text().replace('/usr/bin/phoc', '/usr/local/libexec/aura-phoc-crossfade'), 0o755)

# Stock firmware resets NAS usage at boot; preserve the tested volatile setup.
data_mode = OUT / 'cellular/aura-modem-data-mode'
assert hashlib.sha256(data_mode.read_bytes()).hexdigest() == '9abbc20e73681cd1ee6dcc8e7b08eda5d92f2db60269c18def15669cd815e227'
shutil.copyfile(data_mode, ROOT / 'usr/local/libexec/aura-modem-data-mode')
(ROOT / 'usr/local/libexec/aura-modem-data-mode').chmod(0o755)
link('/etc/systemd/system/ModemManager.service.wants/aura-modem-data-mode.service', '/etc/systemd/system/aura-modem-data-mode.service')
link('/etc/systemd/system/default.target.wants/81voltd.service', '/usr/lib/systemd/system/81voltd.service')
link('/usr/sbin/aura-logo', '/usr/local/sbin/aura-logo')

release = (PROJECT / 'build/mainline/kernel-release.txt').read_text().strip()
modules = Path('/var/tmp/aura-mainline-6.18.2/module-install/lib/modules') / release
assert modules.is_dir()
shutil.copytree(modules, ROOT / 'usr/lib/modules' / release, symlinks=True, dirs_exist_ok=True)
logo_modules = PROJECT / 'build/kali/logo-modules'
if logo_modules.is_dir():
    logo_destination = ROOT / 'usr/lib/modules' / release / 'updates/aura'
    logo_destination.mkdir(parents=True, exist_ok=True)
    for name in ('leds-lp55xx-common.ko', 'leds-lp5523.ko'):
        shutil.copy2(logo_modules / name, logo_destination / name)
torch_module = PROJECT / 'build/kali/torch/leds-aura-lm3644.ko'
if torch_module.is_file():
    torch_destination = ROOT / 'usr/lib/modules' / release / 'updates/aura'
    torch_destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(torch_module, torch_destination / torch_module.name)
camera_module = PROJECT / 'build/kali/camera-startup/imx363.ko'
if camera_module.is_file():
    camera_destination = ROOT / 'usr/lib/modules' / release / 'updates/aura'
    camera_destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(camera_module, camera_destination / camera_module.name)
camera_userspace = PROJECT / 'build/kali/camera/aura-libcamera-focus-timing-trial.tar.gz'
focus_module = PROJECT / 'build/kali/focus/bu64753.ko'
if focus_module.is_file():
    focus_destination = ROOT / 'usr/lib/modules' / release / 'updates/aura'
    focus_destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(focus_module, focus_destination / focus_module.name)
if camera_userspace.is_file():
    with tarfile.open(camera_userspace) as archive:
        assert all(member.name == 'opt' or member.name.startswith('opt/aura-camera') for member in archive.getmembers())
        archive.extractall(ROOT, filter='data')
(ROOT / 'usr/lib/modules' / release / 'build').unlink(missing_ok=True)
run('depmod', '-b', str(ROOT), release)

if subprocess.run(['chroot', str(ROOT), 'id', 'kali'], stdout=subprocess.DEVNULL).returncode:
    chroot('useradd', '-m', '-u', '1000', '-s', '/bin/bash', 'kali')
chroot('chpasswd', input=f'kali:{TEST_PIN}\n', text=True)
assert chroot('id', '-u', 'kali', capture_output=True, text=True).stdout.strip() == '1000'
for group in ('sudo', 'video', 'render', 'input', 'audio', 'plugdev', 'netdev', 'feedbackd'):
    if subprocess.run(['chroot', str(ROOT), 'getent', 'group', group], stdout=subprocess.DEVNULL).returncode == 0:
        chroot('usermod', '-aG', group, 'kali')

# A local, per-port key authenticates USB access; no password SSH listener.
keys = PROJECT / 'device-data/kali-access'
keys.mkdir(parents=True, exist_ok=True)
private = keys / 'id_ed25519'
if not private.exists():
    run('ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'aura-local-development', '-f', str(private))
pub = private.with_suffix('.pub').read_text()
for home, uid in [('root', 0), ('home/kali', 1000)]:
    directory = ROOT / home / '.ssh'
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    write(home + '/.ssh/authorized_keys', pub, 0o600)
    os.chown(directory, uid, uid)
    os.chown(directory / 'authorized_keys', uid, uid)
chroot('ssh-keygen', '-A')
hostkey = (ROOT / 'etc/ssh/ssh_host_ed25519_key.pub').read_text().split()
(keys / 'known_hosts').write_text('192.0.2.1 ' + ' '.join(hostkey[:2]) + '\n')

for unit in ('aura-usb-gadget.service', 'aura-usb-dhcp.service', 'aura-first-boot-guard.service', 'aura-cpu-boost.service', 'ssh.service'):
    link('/etc/systemd/system/multi-user.target.wants/' + unit, '/etc/systemd/system/' + unit if unit.startswith('aura-') else '/usr/lib/systemd/system/' + unit)
link('/etc/systemd/system/graphical.target.wants/phosh.service', '/usr/lib/systemd/system/phosh.service')
link('/etc/systemd/system/sleep.target.wants/aura-bluetooth-sleep.service', '/etc/systemd/system/aura-bluetooth-sleep.service')
link('/etc/systemd/system/default.target', '/usr/lib/systemd/system/graphical.target')
for unit in ('getty@tty1.service', 'greetd.service', 'ssh.socket', 'systemd-firstboot.service', 'systemd-repart.service', 'systemd-growfs-root.service', 'systemd-growfs@.service', 'apt-daily.timer', 'apt-daily-upgrade.timer', 'fstrim.timer', 'NetworkManager-wait-online.service'):
    link('/etc/systemd/system/' + unit, '/dev/null')
write('/etc/systemd/journald.conf.d/10-aura-trial.conf', '[Journal]\nStorage=volatile\nRuntimeMaxUse=96M\n')
# GL applications use software Mesa until the separate GPU port is validated.
write('/etc/environment', '')
chroot('dconf', 'update')
(ROOT / 'usr/sbin/policy-rc.d').unlink(missing_ok=True)
write('/etc/machine-id', '')
(ROOT / 'var/lib/dbus/machine-id').unlink(missing_ok=True)
link('/var/lib/dbus/machine-id', '/etc/machine-id')
chroot('apt-get', 'clean')
chroot('dpkg', '--audit')
manifest = chroot('dpkg-query', '-W', capture_output=True, text=True).stdout
(OUT / 'packages.txt').write_text(manifest)
# Do not ship the WSL resolver copied into the build chroot.
link('/etc/resolv.conf', '/run/NetworkManager/resolv.conf')
print('Configured native Kali trial root, kernel modules, USB SSH and Phosh; userdata is untouched.')
