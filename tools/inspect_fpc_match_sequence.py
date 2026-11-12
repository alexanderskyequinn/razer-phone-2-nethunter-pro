"""Disassemble bounded stock firmware routines; no device or user data access."""
import json
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN
root = Path(__file__).resolve().parents[1]
base = root/'build/kali/fingerprint'
data = (base/'fpctzappfingerprint.elf').read_bytes()
hdr = struct.unpack_from('<16sHHIIIIIHHHHHH', data)
assert data[:6] == b'\x7fELF\x01\x01'
segments = [struct.unpack_from('<8I', data, hdr[5]+i*hdr[9]) for i in range(hdr[10])]
symbols = json.loads((base/'ta-symbols.json').read_text())
names = {s['value'] & ~1: s['name'] for s in symbols if s['name']}
selected = {'fpc_ta_bio_command_handler', 'fpc_algo_begin_identify', 'fpc_algo_identify', 'fpc_algo_end_identify'}
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
out = []
for symbol in symbols:
    if symbol['name'] not in selected: continue
    start = symbol['value'] & ~1
    segment = next(p for p in segments if p[0] == 1 and p[2] <= start and start+symbol['size'] <= p[2]+p[4])
    offset = segment[1] + start-segment[2]
    out.append('\n'+symbol['name'])
    for ins in md.disasm(data[offset:offset+symbol['size']], start):
        target = ''
        if ins.mnemonic in ('bl', 'b.w') and ins.op_str.startswith('#'):
            target = names.get(int(ins.op_str[1:], 0) & ~1, '')
        out.append(f'{ins.address:08x}: {ins.mnemonic:10s} {ins.op_str:28s} {target}')
(base/'match-sequence-disassembly.txt').write_text('\n'.join(out)+'\n')
print('Wrote bounded stock matching disassembly')
