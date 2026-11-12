"""Read-only inspection of the official factory bootloader's GPT writer."""
from pathlib import Path
import capstone
from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_REG

p=Path('build/kali/factory-reference/abl.efi')
data=p.read_bytes()
targets={}
for s in [b'Gpt Image size is invalid',b'GPT: Error processing primary GPT header',
          b'Error writing protective MBR',b'Updated Partition Table Successfully',
          b'Failed to patch GPT',b'Error writing primary GPT header',
          b'Error writing secondary GPT header',b'ValidateSlotGuids:']:
    pos=data.find(s)
    if pos>=0:targets[pos]=s.decode()
md=capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM)
md.detail=True
instructions=list(md.disasm(data[0x1000:0x61000],0x1000))
values={}
found=[]
for n,i in enumerate(instructions):
    ops=i.operands
    if i.mnemonic in ('adrp','adr') and len(ops)==2:
        values[ops[0].reg]=ops[1].imm
    elif i.mnemonic=='add' and len(ops)==3 and ops[2].type==ARM64_OP_IMM:
        if ops[1].reg in values:
            val=values[ops[1].reg]+ops[2].imm
            values[ops[0].reg]=val
            if val in targets:
                found.append((n,targets[val]))
    elif i.mnemonic in ('ret','b'):
        values.clear()
out=[]
for n,s in found:
    out.append(f'\nREFERENCE {s} at {instructions[n].address:x}')
    for i in instructions[max(n-24,0):n+14]:
        out.append(f'{i.address:08x}  {i.mnemonic:8} {i.op_str}')
Path('build/kali/factory-reference/gpt-writer-references.txt').write_text('\n'.join(out))
print('\n'.join(f'{instructions[n].address:x}: {s}' for n,s in found))
