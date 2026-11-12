"""Cross-build discovery-only libfprint against the existing Kali build sysroot."""
from pathlib import Path
import hashlib,json,os,shlex,shutil,subprocess,urllib.request
root=Path(__file__).resolve().parents[1]
work=Path('/var/tmp/aura-libfprint-platform');sysroot=Path('/var/tmp/aura-kali-rootfs')
def run(*cmd,**kw):return subprocess.run(cmd,check=True,**kw)
downloaded=[]
for package in ['libgusb-dev','libusb-1.0-0-dev']:
    raw=subprocess.check_output(['chroot',str(sysroot),'apt-cache','show',package],text=True)
    info={k:v.strip() for line in raw.split('\n\n')[0].splitlines() if ': ' in line for k,v in [line.split(': ',1)]}
    assert info['Architecture']=='arm64'
    data=urllib.request.urlopen('https://kali.download/kali/'+info['Filename'],timeout=45).read()
    assert len(data)==int(info['Size']) and hashlib.sha256(data).hexdigest()==info['SHA256']
    path=work/Path(info['Filename']).name;path.write_bytes(data)
    run('dpkg-deb','-x',str(path),str(sysroot))
    downloaded.append({k:info[k] for k in ('Package','Version','SHA256')})
cross=work/'arm64.ini'
cross.write_text(f'''[binaries]
c = 'aarch64-linux-gnu-gcc'
cpp = 'aarch64-linux-gnu-g++'
ar = 'aarch64-linux-gnu-ar'
strip = 'aarch64-linux-gnu-strip'
pkg-config = 'pkg-config'
exe_wrapper = ['qemu-aarch64', '-L', '{sysroot}']
[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
[properties]
sys_root = '{sysroot}'
pkg_config_libdir = ['{sysroot}/usr/lib/aarch64-linux-gnu/pkgconfig', '{sysroot}/usr/share/pkgconfig']
[built-in options]
c_args = ['--sysroot={sysroot}']
cpp_args = ['--sysroot={sysroot}']
c_link_args = ['--sysroot={sysroot}', '-Wl,-rpath-link,{sysroot}/usr/lib/aarch64-linux-gnu']
cpp_link_args = ['--sysroot={sysroot}', '-Wl,-rpath-link,{sysroot}/usr/lib/aarch64-linux-gnu']
''')
run('meson','setup',str(work/'arm64'),str(work/'source'),'--cross-file',str(cross),'--prefix=/opt/aura-fprint-discovery','-Ddrivers=aura_fpc','-Dintrospection=false','-Ddoc=false','-Dinstalled-tests=false','-Dudev_rules=disabled','-Dudev_hwdb=disabled')
run('ninja','-C',str(work/'arm64'),'libfprint/libfprint-2.so.2.0.0')
env=dict(os.environ,PKG_CONFIG_SYSROOT_DIR=str(sysroot),PKG_CONFIG_LIBDIR=f'{sysroot}/usr/lib/aarch64-linux-gnu/pkgconfig:{sysroot}/usr/share/pkgconfig')
flags=shlex.split(subprocess.check_output(['pkg-config','--cflags','--libs','glib-2.0','gio-2.0'],env=env,text=True))
out=root/'build/kali/fingerprint/libfprint-platform';out.mkdir(parents=True,exist_ok=True)
run('aarch64-linux-gnu-gcc',f'--sysroot={sysroot}','-Wall','-Wextra','-Werror',str(root/'tests/fprint-platform-enumerate.c'),f'-I{work}/source',f'-I{work}/arm64/libfprint',*flags,f'-L{work}/arm64/libfprint',f'-Wl,-rpath-link,{sysroot}/usr/lib/aarch64-linux-gnu','-Wl,-rpath,$ORIGIN','-lfprint-2','-o',str(out/'enumerate'))
shutil.copy2(work/'arm64/libfprint/libfprint-2.so.2.0.0',out/'libfprint-2.so.2')
(out/'build.json').write_text(json.dumps({'stage':'discovery only; not installed system-wide','packages':downloaded,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.name!='build.json'}},indent=2)+'\n')
print(out)
