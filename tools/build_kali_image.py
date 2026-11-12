"""Make a checked ext4 + Android sparse userdata image in WSL; no phone writes."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

PROJECT = Path(__file__).resolve().parents[1]
ROOT = Path('/var/tmp/aura-kali-rootfs')
WORK = Path('/var/tmp/aura-kali-build/images')
OUT = PROJECT / 'build/kali'
identity = json.loads((OUT / 'identity.json').read_text())
assert (ROOT / 'etc/aura-install-id').read_text().strip() == identity['install_id']
# Never image an active chroot or include its proc/dev/sys mounts.
mounts = subprocess.check_output(['findmnt', '-rn', '-o', 'TARGET'], text=True).splitlines()
assert not any(p == str(ROOT) or p.startswith(str(ROOT) + '/') for p in mounts), 'chroot still mounted'
audit = subprocess.check_output(['chroot', str(ROOT), 'dpkg', '--audit'], text=True)
assert not audit.strip(), audit
for name in ('usr/bin/phosh-session', 'usr/bin/phoc', 'usr/bin/phosh-osk-stevia', 'usr/local/libexec/aura-phoc-crossfade', 'usr/local/libexec/aura-phosh-crossfade-session', 'usr/local/libexec/aura-modem-data-mode', 'usr/sbin/ModemManager', 'usr/bin/qmicli', 'usr/bin/81voltd', 'usr/bin/gnome-calls', 'usr/bin/chatty', 'usr/local/sbin/aura-usb-gadget', 'usr/sbin/sshd', 'etc/aura-install-id'):
    assert (ROOT / name).is_file(), name
usage = int(subprocess.check_output(['du', '-sx', '-B1', str(ROOT)], text=True).split()[0])
gib = 1024 ** 3
size = max(6 * gib, ((usage * 13 // 10 + gib + gib - 1) // gib) * gib)
assert size <= 20 * gib, f'Unexpected rootfs size: {size}'
WORK.mkdir(parents=True, exist_ok=True)
raw = WORK / 'aura-kali-trial-v1.ext4'
assert not raw.exists(), 'Refusing to overwrite a previously built image'
with raw.open('xb') as f:
    f.truncate(size)
subprocess.run(['mke2fs', '-q', '-F', '-t', 'ext4', '-b', '4096', '-L', 'aura-kali', '-U', identity['root_uuid'], '-m', '0', '-E', 'lazy_itable_init=0,lazy_journal_init=0', '-d', str(ROOT), str(raw)], check=True)
check = subprocess.run(['e2fsck', '-fn', str(raw)], capture_output=True, text=True)
(OUT / 'filesystem-check.txt').write_text(check.stdout + check.stderr)
assert check.returncode == 0, check.stdout + check.stderr
fs_id = subprocess.check_output(['blkid', '-p', '-o', 'export', str(raw)], text=True)
assert 'UUID=' + identity['root_uuid'] in fs_id and 'TYPE=ext4' in fs_id
sparse = OUT / 'aura-kali-trial-v1-userdata.img'
assert not sparse.exists(), 'Refusing to overwrite a previously built sparse image'
subprocess.run(['img2simg', str(raw), str(sparse)], check=True)
def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()
manifest = {'identity': identity, 'created_epoch': time.time(), 'root_tree_bytes': usage, 'expanded_bytes': size, 'raw_path_wsl': str(raw), 'sparse_file': sparse.name, 'sparse_bytes': sparse.stat().st_size, 'sparse_sha256': sha(sparse), 'filesystem_check_exit': check.returncode, 'target_partition': 'userdata', 'warning': 'Flashing replaces Android userdata; do not boot Android afterwards unless intentionally recovering it.'}
(OUT / 'rootfs-manifest.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
