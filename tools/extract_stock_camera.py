"""Read the phone's retained QTI symbol/data sections; extract sensor registers only."""
from pathlib import Path
import struct
import json
root=Path(__file__).resolve().parents[1]
path=root/'device-data/camera-reference/com.qti.sensormodule.liteon_imx363.bin'
data=path.read_bytes()
assert data.startswith(b'QTI Chromatix Header')
symbol_base,symbol_size=struct.unpack_from('<QQ',data,168)
data_base,data_size=struct.unpack_from('<QQ',data,192)
assert symbol_size%72==0 and data_base+data_size <= len(data)
symbols={}
for off in range(symbol_base,symbol_base+symbol_size,72):
    ident,name,version,mode,start,size=struct.unpack_from('<Q32sQQQQ',data,off)
    assert start+size<=data_size and size%8==0
    symbols[ident]={'name':name.split(b'\0')[0].decode(), 'values':list(struct.unpack_from('<'+'Q'*(size//8),data,data_base+start))}
tables=[]
for ident,s in symbols.items():
    if s['name']!='regSetting': continue
    # Later tables are OIS/EEPROM/flash, not sensor settings.
    if ident>=1789: continue
    assert len(s['values'])%10==0
    regs=[]
    for start in range(0,len(s['values']),10):
        v=s['values'][start:start+10]
        assert symbols[v[4]]['name']=='registerData'
        regs.append({'address':v[2], 'data':symbols[v[4]]['values'], 'address_type':v[5], 'data_type':v[6], 'operation':v[7], 'delay_us':symbols[v[9]]['values']})
    tables.append({'symbol':ident,'registers':regs})
(root/'device-data/camera-reference/imx363-tables.json').write_text(json.dumps({'symbols':symbols,'tables':tables},indent=2)+'\n')
for table in tables:
    regs=table['registers']
    print('table',table['symbol'],'registers',len(regs), 'first',[(hex(r['address']),r['data']) for r in regs[:3]])
    if table['symbol']==23:
        print(' '.join(f"{r['address']:04x}={r['data'][0]:02x}" for r in regs))
