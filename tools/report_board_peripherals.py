"""Resolve stock board peripheral supply references from the captured DTB."""
import json, struct
from check_board_memory import live

phandles = {struct.unpack('>I', p['phandle'])[0]: n for n,p in live.items() if 'phandle' in p}
def fmt(v):
    if v and v[-1:] == b'\0' and all(x == 0 or 32 <= x < 127 for x in v): return v.rstrip(b'\0').decode().replace('\0', ', ')
    if len(v)%4 == 0: return [hex(x) for x in struct.unpack('>'+'I'*(len(v)//4),v)]
    return v.hex()
result = {}
for n,p in live.items():
    if any(s in n for s in ('icnss@', 'bt_wcn3990', 'rmtfs', 'rmt_storage', 'serial@', 'gpio-keys')):
        item = {k:fmt(v) for k,v in p.items() if k not in ('phandle',)}
        for k,v in p.items():
            if (k.endswith('-supply') or k.startswith('pinctrl-')) and len(v) == 4:
                ref=phandles.get(struct.unpack('>I',v)[0])
                if ref: item[k] = dict(node=ref, properties={a:fmt(b) for a,b in live[ref].items() if a != 'phandle'})
        result[n]=item
print(json.dumps(result,indent=2))
