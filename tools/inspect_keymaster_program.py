"""Offline inspection of the signed vendor program; no phone access."""
import json
from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

root = Path(__file__).resolve().parents[1]
b = (root / 'build/kali/fingerprint/keymaster64.elf').read_bytes()
h = struct.unpack_from('<16sHHIQQQIHHHHHH', b)
segments = [struct.unpack_from('<IIQQQQQQ', b, h[5] + i*h[9]) for i in range(h[10])]
def offset(address):
    for p in segments:
        if p[0] == 1 and p[3] <= address < p[3] + p[5]:
            return p[2] + address - p[3]
    raise ValueError(hex(address))
dynamic = next(p for p in segments if p[0] == 2)
tags = dict(struct.unpack_from('<QQ',b,i) for i in range(dynamic[2], dynamic[2]+dynamic[5],16))
count=struct.unpack_from('<II',b,offset(tags[4]))[1]
symbols=[]
for i in range(count):
    name,info,other,section,value,size=struct.unpack_from('<IBBHQQ',b,offset(tags[6])+i*tags[11])
    n=offset(tags[5])+name
    text=b[n:b.index(b'\0',n)].decode(errors='replace')
    symbols.append(dict(name=text,value=value,size=size,info=info,section=section))
(root/'build/kali/fingerprint/keymaster-symbols.json').write_text(json.dumps(symbols,indent=2)+'\n')
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
imports={}
for i in range(offset(tags[23]),offset(tags[23])+tags[2],24):
    address,info,addend=struct.unpack_from('<QQq',b,i)
    imports[address]=symbols[info >> 32]['name']
print('Storage-related imported calls:')
for address,name in imports.items():
    if any(x in name for x in ('stor','rpmb','listener')):
        print(hex(address),name)
lines=[]
for p in segments:
    if p[0] == 1 and p[1] & 1:
        for ins in md.disasm(b[p[2]:p[2]+p[5]],p[3]):
            lines.append(f'{ins.address:08x}: {ins.mnemonic}\t{ins.op_str}')
(root/'test-runs/snapshot/keymaster-ta-disassembly.txt').write_text('\n'.join(lines)+'\n')
print('Symbols:',len(symbols),'Instructions:',len(lines))
for s in symbols:
    if any(x in s['name'].lower() for x in ('enroll','gate','rpmb','verif','command')):
        print(s)
for needle in (b'enroll\0', b'deserializeEnroll\0', b'GK_ENROLL\0', b'!!! secboot device'):
    start=0
    while (o:=b.find(needle,start)) >= 0:
        for p in segments:
            if p[0] == 1 and p[2] <= o < p[2]+p[5]: print(needle,hex(p[3]+o-p[2]))
        start=o+1
