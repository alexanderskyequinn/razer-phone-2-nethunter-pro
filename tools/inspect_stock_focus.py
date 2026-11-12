"""Locate stock focus routine string references in the retained ARM Thumb HAL."""
from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from capstone.arm import ARM_OP_REG, ARM_OP_MEM, ARM_REG_PC
root=Path(__file__).resolve().parents[1]
data=(root/'device-data/camera-reference/camera.qcom.so').read_bytes()
shoff=struct.unpack_from('<I',data,32)[0]
ents,count,names=struct.unpack_from('<HHH',data,46)
sections=[struct.unpack_from('<10I',data,shoff+i*ents) for i in range(count)]
name_sec=sections[names]
strings=data[name_sec[4]:name_sec[4]+name_sec[5]]
byname={strings[s[0]:].split(b'\0')[0].decode():s for s in sections}
text=byname['.text']
def word(address):
    for s in sections:
        if s[3]<=address and address+4<=s[3]+s[5] and s[1]!=8:
            return struct.unpack_from('<I',data,s[4]+address-s[3])[0]
    return None
engine=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
engine.detail=True
engine.skipdata=True
pending={}
matches=[]
for ins in engine.disasm(data[text[4]:text[4]+text[5]],text[3]):
    if not ins.id: continue
    ops=ins.operands
    if ins.mnemonic.startswith('ldr') and len(ops)==2 and ops[0].type==ARM_OP_REG and ops[1].type==ARM_OP_MEM and ops[1].mem.base==ARM_REG_PC:
        addr=((ins.address+4)&~3)+ops[1].mem.disp
        value=word(addr)
        if value is not None: pending[ops[0].reg]=(value,ins.address)
    elif ins.mnemonic.startswith('add') and len(ops)==2 and all(o.type==ARM_OP_REG for o in ops) and ops[1].reg==ARM_REG_PC and ops[0].reg in pending:
        value,origin=pending.pop(ops[0].reg)
        target=(ins.address+4+value)&0xffffffff
        if 0x3376ab<=target<=0x337822:
            matches.append(f'{origin:#x} -> {ins.address:#x} -> string {target:#x}')
(root/'device-data/camera-reference/focus-xrefs.txt').write_text('\n'.join(matches)+'\n')
print('\n'.join(matches))
