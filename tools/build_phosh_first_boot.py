"""Cross-build the pinned upstream wizard; tools and dependencies stay in /var/tmp."""
from pathlib import Path
import hashlib,os,shutil,subprocess,urllib.request
project=Path(__file__).resolve().parents[1]
source=project/'sources/phosh-first-boot'
work=Path('/var/tmp/aura-phosh-first-boot')
work.mkdir(exist_ok=True)
env=dict(os.environ,CARGO_HOME='/var/tmp/aura-cargo',RUSTUP_HOME='/var/tmp/aura-rustup')
env['PATH']=env['CARGO_HOME']+'/bin:'+env['PATH']
def run(*cmd,**kwargs):return subprocess.run(cmd,check=True,env=env,**kwargs)
assert subprocess.check_output(['git','-c',f'safe.directory={source}','-C',str(source),'rev-parse','HEAD'],text=True).strip()=='9c69b23ff4029d48efd6dcd0b9d6287dbc12d9d8'
if not Path(env['CARGO_HOME']+'/bin/rustup').exists():
    url='https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init'
    data=urllib.request.urlopen(url,timeout=60).read()
    digest=urllib.request.urlopen(url+'.sha256',timeout=30).read().decode().split()[0]
    assert hashlib.sha256(data).hexdigest()==digest
    tool=work/'rustup-init';tool.write_bytes(data);tool.chmod(0o755)
    run(str(tool),'-y','--no-modify-path','--profile','minimal','--default-toolchain','1.95.0','--target','aarch64-unknown-linux-gnu')
else:
    run('rustup','toolchain','install','1.95.0','--profile','minimal','--target','aarch64-unknown-linux-gnu')
tree=work/'source'
if not tree.exists(): shutil.copytree(source,tree,ignore=shutil.ignore_patterns('.git'))
sysroot='/var/tmp/aura-kali-rootfs'
linker=work/'aarch64-linker'
linker.write_text('#!/bin/sh\nexec aarch64-linux-gnu-gcc --sysroot='+sysroot+' -Wl,-rpath-link,'+sysroot+'/usr/lib/aarch64-linux-gnu "$@"\n')
linker.chmod(0o755)
env.update(PFB_SKIP_MESON='1',PKG_CONFIG_ALLOW_CROSS='1',PKG_CONFIG_SYSROOT_DIR_aarch64_unknown_linux_gnu=sysroot,
           PKG_CONFIG_LIBDIR_aarch64_unknown_linux_gnu=sysroot+'/usr/lib/aarch64-linux-gnu/pkgconfig:'+sysroot+'/usr/share/pkgconfig',
           CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=str(linker),
           CARGO_TARGET_DIR=str(work/'target'),CC_aarch64_unknown_linux_gnu='aarch64-linux-gnu-gcc')
# Distribution paths, not behavioral source modifications.
(tree/'src/pfb/config.rs').write_text('pub static APP_ID: &str = "mobi.phosh.FirstBoot";\npub static DEFAULTSDIR: &str = "/usr/share/phosh-first-boot";\npub static GETTEXT_PACKAGE: &str = "phosh-first-boot";\npub static OUTPUTDIR: &str = "/run/phosh-first-boot";\npub static LOCALEDIR: &str = "/usr/share/locale";\n')
run('cargo','+1.95.0','build','--locked','--release','--target','aarch64-unknown-linux-gnu','-j','4',cwd=tree)
out=project/'build/kali/upstream-onboarding';out.mkdir(parents=True,exist_ok=True)
for name in ('phosh-first-boot','phosh-first-boot-importer'):
    shutil.copy2(work/'target/aarch64-unknown-linux-gnu/release'/name,out/name)
print('Pinned upstream first-boot binaries built.')
