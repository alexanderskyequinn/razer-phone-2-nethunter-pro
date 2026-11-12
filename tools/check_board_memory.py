"""Check that every fixed live-board reserved interval remains reserved."""
import json
from pathlib import Path
import struct


def read_fdt(path):
    data=path.read_bytes()
    magic,total,off_struct,off_strings=struct.unpack_from('>4I',data)
    assert magic==0xd00dfeed and total==len(data)
    stack=[]; nodes={}; pos=off_struct
    while True:
        token=struct.unpack_from('>I',data,pos)[0]; pos+=4
        if token==1:
            end=data.index(0,pos); name=data[pos:end].decode()
            stack.append(name); pos=(end+4)&~3
            nodes['/'+'/'.join(stack[1:])]={}
        elif token==2:
            stack.pop()
        elif token==3:
            size,nameoff=struct.unpack_from('>II',data,pos); pos+=8
            start=off_strings+nameoff; end=data.index(0,start)
            name=data[start:end].decode()
            nodes['/'+'/'.join(stack[1:])][name]=data[pos:pos+size]
            pos=(pos+size+3)&~3
        elif token==4:
            continue
        elif token==9:
            break
        else:
            raise ValueError(token)
    return nodes


def fixed_regions(nodes):
    regions=[]
    for name,props in nodes.items():
        if name.startswith('/reserved-memory/') and name.count('/')==2 and 'reg' in props:
            data=props['reg']; assert len(data)%16==0
            for pos in range(0,len(data),16):
                start,size=struct.unpack_from('>QQ',data,pos)
                regions.append((start,start+size,name))
    return sorted(regions)


root=Path(__file__).resolve().parents[1]
live=read_fdt(root/'device-data/20261006-181410-429985/live.dtb')
new=read_fdt(root/'build/mainline/sdm845-razer-aura.dtb')
old_regions=fixed_regions(live); new_regions=fixed_regions(new)
missing=[]
for start,end,name in old_regions:
    position=start
    for low,high,_ in new_regions:
        if low<=position<high: position=min(end,high)
    if position<end: missing.append({'node':name,'first_uncovered':hex(position),'end':hex(end)})
report={'all_live_fixed_reservations_preserved':not missing,'missing':missing,
        'live':[{'node':n,'start':hex(a),'end':hex(b)} for a,b,n in old_regions],
        'new':[{'node':n,'start':hex(a),'end':hex(b)} for a,b,n in new_regions]}
(root/'build/mainline/memory-check.json').write_text(json.dumps(report,indent=2))
assert not missing, missing
for property_name in ('qcom,msm-id','qcom,board-id','fih,hw-id'):
    assert new['/'][property_name]==live['/'][property_name],property_name
print(f'All {len(old_regions)} fixed live reserved regions covered; SoC, board and FIH IDs match.')
