"""Build GNOME's standard prompt client against verified Kali development files."""
from pathlib import Path
import hashlib
import os
import shlex
import subprocess
import urllib.request

root = Path(__file__).resolve().parents[1]
sysroot = Path('/var/tmp/aura-kali-rootfs')
out = root / 'build/kali/fingerprint'
cache = Path('/var/tmp/aura-fprint-prompt-build')
cache.mkdir(exist_ok=True)
for package in ('libgcr-4-dev', 'libgck-2-dev', 'libp11-kit-dev', 'libgcrypt20-dev', 'libgpg-error-dev'):
    raw = subprocess.check_output(['chroot', str(sysroot), 'apt-cache', 'show', package], text=True)
    info = dict(line.split(': ', 1) for line in raw.split('\n\n')[0].splitlines() if ': ' in line)
    assert info['Architecture'] == 'arm64'
    archive = cache / Path(info['Filename']).name
    if not archive.exists():
        archive.write_bytes(urllib.request.urlopen('https://kali.download/kali/' + info['Filename'], timeout=40).read())
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == info['SHA256']
    subprocess.run(['dpkg-deb', '-x', str(archive), str(sysroot)], check=True)
env = dict(os.environ, PKG_CONFIG_SYSROOT_DIR=str(sysroot),
           PKG_CONFIG_LIBDIR=f'{sysroot}/usr/lib/aarch64-linux-gnu/pkgconfig:{sysroot}/usr/share/pkgconfig')
flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'gcr-4', 'libgcrypt'], env=env, text=True))
binary = out / 'aura-fprint-prompt'
subprocess.run(['aarch64-linux-gnu-gcc', f'--sysroot={sysroot}', '-Wall', '-Wextra', '-Werror', '-O2',
                str(root/'port/aura-fingerprint/aura-fprint-prompt.c'), *flags,
                f'-Wl,-rpath-link,{sysroot}/usr/lib/aarch64-linux-gnu', '-o', str(binary)], check=True)
print(hashlib.sha256(binary.read_bytes()).hexdigest(), binary)
