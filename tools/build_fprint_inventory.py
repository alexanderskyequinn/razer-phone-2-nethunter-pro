from pathlib import Path
import os
import shlex
import subprocess
root = Path(__file__).resolve().parents[1]
sysroot = '/var/tmp/aura-kali-rootfs'
work = '/var/tmp/aura-libfprint-operations'
env = dict(os.environ, PKG_CONFIG_SYSROOT_DIR=sysroot,
           PKG_CONFIG_LIBDIR=f'{sysroot}/usr/lib/aarch64-linux-gnu/pkgconfig:{sysroot}/usr/share/pkgconfig')
flags = shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'gio-2.0'], env=env, text=True))
subprocess.run(['aarch64-linux-gnu-gcc', f'--sysroot={sysroot}', '-Wall', '-Wextra', '-Werror',
    str(root/'diagnostic/fprint-device-inventory.c'), f'-I{work}/source', f'-I{work}/arm64/libfprint',
    *flags, f'-L{work}/arm64/libfprint', f'-Wl,-rpath-link,{sysroot}/usr/lib/aarch64-linux-gnu',
    '-lfprint-2', '-o', str(root/'build/kali/fingerprint/libfprint-operations/fprint-device-inventory')], check=True)
