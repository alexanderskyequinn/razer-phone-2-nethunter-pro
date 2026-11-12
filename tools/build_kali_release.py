"""Build portable boot and sparse ext4 userdata artifacts; never flashes a phone."""
from pathlib import Path
import gzip,hashlib,json,shutil,subprocess,sys,uuid
from pack_diagnostic import archive_entry
project=Path(__file__).resolve().parents[1]
root=Path('/var/tmp/aura-kali-release-rootfs')
release=project/'build/kali/release'
out=release/'candidate-2-stock-setup'
out.mkdir(parents=True,exist_ok=True)
assert not (out/'aura-kali-userdata.img').exists(),'Refusing to overwrite an existing candidate'
subprocess.run([sys.executable,str(project/'tools/audit_kali_release.py')],check=True)
mounts=subprocess.check_output(['findmnt','-rn','-o','TARGET'],text=True).splitlines()
assert not any(p==str(root) or p.startswith(str(root)+'/') for p in mounts)
work=Path('/var/tmp/aura-kali-release-images/candidate-2-stock-setup');work.mkdir(parents=True,exist_ok=True)
base=project/'build/kali/fpc-resources-test/aura-kali-v26-fpc-resources.img'
assert hashlib.sha256(base.read_bytes()).hexdigest()=='2fdfb649c979f70ebc44c82c9d33c9a7580e2f67e2e798b5f9567a8396cd8abd'
subprocess.run([sys.executable,str(project/'sources/mkbootimg/unpack_bootimg.py'),'--boot_img',str(base),'--out',str(work/'base')],check=True,stdout=subprocess.DEVNULL)
entries=[(p,b'',0o040755,(0,0)) for p in ('bin','dev','proc','sys','run','newroot','lib','lib/firmware','lib/firmware/qcom','lib/firmware/qcom/sdm845','lib/firmware/qcom/sdm845/razer','lib/firmware/qcom/sdm845/razer/aura')]
for name in ('busybox','return-to-bootloader'):
    entries.append(('bin/'+name,(project/'build/diagnostic'/name).read_bytes(),0o100755,(0,0)))
entries.extend([('bin/sh',b'busybox',0o120777,(0,0)),('init',(project/'port/aura-setup/init').read_bytes().replace(b'\r\n',b'\n'),0o100755,(0,0)),('dev/console',b'',0o020600,(5,1)),('dev/null',b'',0o020666,(1,3))])
for name in ('qcom/a630_sqe.fw','qcom/a630_gmu.bin',*(f'qcom/sdm845/razer/aura/a630_zap.{ext}' for ext in ('mdt','b00','b01','b02'))):
    entries.append(('lib/firmware/'+name,(root/'usr/lib/firmware'/name).read_bytes(),0o100644,(0,0)))
archive=b''.join(archive_entry(n,p,m,i,d) for i,(n,p,m,d) in enumerate(entries,1))+archive_entry('TRAILER!!!')
archive+=b'\0'*(-len(archive)%512)
ramdisk=work/'initramfs.cpio.gz';ramdisk.write_bytes(gzip.compress(archive,mtime=0))
boot=out/'aura-kali-boot.img'
subprocess.run([sys.executable,str(project/'sources/mkbootimg/mkbootimg.py'),'--kernel',str(work/'base/kernel'),'--ramdisk',str(ramdisk),'--header_version','1','--pagesize','4096','--base','0','--kernel_offset','32768','--ramdisk_offset','16777216','--tags_offset','256','--os_version','9.0.0','--os_patch_level','2020-11','--cmdline','console=null rdinit=/init loglevel=3 fw_devlink=permissive panic=10 systemd.gpt_auto=0 systemd.repart=0','--output',str(boot)],check=True)
assert boot.stat().st_size < 67108864
with boot.open('ab') as f:f.write(b'\0'*(67108864-boot.stat().st_size))
subprocess.run([sys.executable,str(project/'sources/mkbootimg/unpack_bootimg.py'),'--boot_img',str(boot),'--out',str(work/'verify')],check=True,stdout=subprocess.DEVNULL)
assert (work/'verify/kernel').read_bytes()==(work/'base/kernel').read_bytes()
assert (work/'verify/ramdisk').read_bytes()==ramdisk.read_bytes()
(out/'blank-dtbo.img').write_bytes(b'\0'*8388608)
usage=int(subprocess.check_output(['du','-sx','-B1',str(root)],text=True).split()[0])
gib=1024**3;size=max(6*gib,((usage*13//10+gib-1)//gib)*gib)
raw=work/'aura-kali-userdata.ext4'
assert not raw.exists(),'Refusing to overwrite an existing candidate image'
with raw.open('xb') as f:f.truncate(size)
subprocess.run(['mke2fs','-q','-F','-t','ext4','-b','4096','-L','aura-kali','-U',str(uuid.uuid4()),'-m','0','-E','lazy_itable_init=0,lazy_journal_init=0','-d',str(root),str(raw)],check=True)
check=subprocess.run(['e2fsck','-fn',str(raw)],capture_output=True,text=True)
(out/'filesystem-check.txt').write_text(check.stdout+check.stderr)
assert check.returncode==0
sparse=out/'aura-kali-userdata.img'
assert not sparse.exists()
subprocess.run(['img2simg',str(raw),str(sparse)],check=True)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
files=[boot,sparse,out/'blank-dtbo.img',out/'recovery/aura-recovery-v1.img']
(out/'recovery').mkdir(exist_ok=True)
for name in ('aura-recovery-v1.img','manifest.json'):
    shutil.copy2(release/'recovery'/name,out/'recovery'/name)
for name in ('onboarding.json','privacy-and-runtime-audit.json','packages.txt'):
    shutil.copy2(release/name,out/name)
manifest={'device':'razer,aura','product':'aura','release':'candidate-2-stock-setup','fresh_install_hardware_tested':False,'redistribution_ready':False,
          'default_credentials':False,'remote_access_default':'disabled','first_run_setup':True,'automatic_root_expansion':True,
          'setup_provider':'phosh-first-boot','login_provider':'phrog','fingerprint_stock_backend_ready':False,
          'root_expanded_bytes':size,'root_tree_bytes':usage,'filesystem_check_exit':check.returncode,
          'firmware_distribution_review_required':True,'files':{str(p.relative_to(out)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in files}}
(out/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'SHA256SUMS').write_text(''.join(v['sha256']+'  '+p+'\n' for p,v in manifest['files'].items()))
print(json.dumps(manifest,indent=2))
