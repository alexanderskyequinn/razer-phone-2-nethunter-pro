"""Build a RAM-only original-kernel probe; never mount a phone partition."""
import gzip, hashlib, json, struct, subprocess, sys
from pathlib import Path
from pack_diagnostic import archive_entry

root = Path(__file__).resolve().parents[1]
capture = root / 'device-data/20261006-181410-429985'
out = root / 'build/stock-memory-probe'
out.mkdir(exist_ok=True)
boot = (capture / 'boot_a.img').read_bytes()
assert hashlib.sha256(boot).hexdigest() == '2072cf0408361e1aa524743821a791b365de12633fcd4d9550b158d8537727fe'
ks, ka, rs, ra, ss, sa, ta, page, ver, osv = struct.unpack_from('<10I', boot, 8)
assert page == 4096 and ver == 1 and ss == 0
kernel = boot[page:page+ks]
(out / 'kernel').write_bytes(kernel)
init = (root / 'diagnostic/init').read_text().replace('AURA_NATIVE_DIAG_V5', 'AURA_STOCK_MEMORY_PROBE').replace('sleep 180', 'sleep 240').replace('180 seconds', '240 seconds')
init = init.replace("echo; echo 'Kernel log:'; dmesg", """echo; echo 'UIO MEMORY MAPS:'
        for node in /sys/class/uio/uio*; do
            echo "$node"; cat "$node/name"
            for map in "$node"/maps/map*; do
                echo "$map"; cat "$map/addr" "$map/size" "$map/offset"
            done
        done
        echo; echo 'Kernel log:'; dmesg""")
assert 'UIO MEMORY MAPS:' in init and 'mount -t ext4' not in init
(out / 'init').write_text(init)
entries = [(n,b'',0o040755,(0,0)) for n in ('bin','dev','proc','sys','run','www','config')]
for n in ('busybox','return-to-bootloader'):
    entries.append(('bin/'+n,(root/'build/diagnostic'/n).read_bytes(),0o100755,(0,0)))
entries += [('bin/sh',b'busybox',0o120777,(0,0)),('init',init.encode(),0o100755,(0,0)),('report-template.img.gz',(root/'build/diagnostic/report-template.img.gz').read_bytes(),0o100644,(0,0)),('dev/console',b'',0o020600,(5,1)),('dev/null',b'',0o020666,(1,3))]
archive = b''.join(archive_entry(n,p,m,i,d) for i,(n,p,m,d) in enumerate(entries,1))+archive_entry('TRAILER!!!')
archive += b'\0'*(-len(archive)%512)
(out/'ramdisk.gz').write_bytes(gzip.compress(archive,mtime=0))
cmdline = (boot[64:576].split(b'\0',1)[0]+boot[608:1632].split(b'\0',1)[0]).decode()+' rdinit=/init loglevel=7'
image=out/'aura-stock-memory-probe.img'
subprocess.run([sys.executable,str(root/'sources/mkbootimg/mkbootimg.py'),'--kernel',str(out/'kernel'),'--ramdisk',str(out/'ramdisk.gz'),'--header_version','1','--pagesize','4096','--base','0','--kernel_offset',str(ka),'--ramdisk_offset',str(ra),'--tags_offset',str(ta),'--os_version','9.0.0','--os_patch_level','2020-11','--cmdline',cmdline,'--output',str(image)],check=True)
assert image.stat().st_size<67108864
with image.open('ab') as f:f.write(b'\0'*(67108864-image.stat().st_size))
subprocess.run([sys.executable,str(root/'sources/mkbootimg/unpack_bootimg.py'),'--boot_img',str(image),'--out',str(out/'roundtrip')],check=True,stdout=subprocess.DEVNULL)
assert (out/'roundtrip/kernel').read_bytes()==kernel
assert (out/'roundtrip/ramdisk').read_bytes()==(out/'ramdisk.gz').read_bytes()
record={'sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'bytes':image.stat().st_size,'scope':'RAM-only original-kernel UIO memory probe, original dtbo_b required, no filesystem mounts, 240-second return to bootloader. Restore blank dtbo_b and native Kali boot_b afterward.'}
(out/'manifest.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))

