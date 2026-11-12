"""Generate public GPT test fixtures; compile actual switching code with no I/O."""
from pathlib import Path
import subprocess,sys,tarfile,struct
from validate_gpt_backup import read_backup
root=Path(__file__).resolve().parents[1]
source=root/'device-data/native-prerequisites/gpt-after-qbootctl-v4-full.tar'
read_backup(source,True,True)
names=[];entries=[]
with tarfile.open(source) as t:
    for disk in ('sda','sdb','sdc','sdd','sde','sdf'):
        raw=t.extractfile(f'aura-gpt-backup/{disk}.start.bin').read()
        sector=next(s for s in (512,4096) if raw[s:s+8]==b'EFI PART')
        lba,count,size=struct.unpack_from('<QII',raw,sector+72)
        for n in range(count):
            e=raw[lba*sector+n*size:lba*sector+(n+1)*size]
            if e[:16]==bytes(16):continue
            assert len(e)==128
            names.append(e[56:].decode('utf-16le').rstrip('\0'))
            entries.append(e)
out=root/'build/kali/rescue'
fixture='#define FIXTURE_COUNT '+str(len(names))+'\n'
fixture+='static const char *fixture_names[] = {'+','.join('"'+n+'"' for n in names)+'};\n'
fixture+='static const unsigned char fixture_entries[][128] = {\n'
fixture+=',\n'.join('{'+','.join(hex(b) for b in e)+'}' for e in entries)+'};\n'
(out/'slot-fixtures.h').write_text(fixture)
if sys.platform!='linux':raise SystemExit('Run this test in WSL')
test=out/'slot-switch-test'
subprocess.run(['gcc','-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
                '-I'+str(root/'sources/qbootctl-recovery'),'-I'+str(out),
                str(root/'tests/test_qbootctl_slots.c'),'-o',str(test)],check=True)
subprocess.run([str(test)],check=True)
