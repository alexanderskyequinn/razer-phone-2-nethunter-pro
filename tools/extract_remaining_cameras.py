"""Decode retained stock camera module symbols without writing to hardware."""
import json
import struct
from pathlib import Path
base = Path(__file__).resolve().parents[1] / 'device-data/camera-reference'
for model, module in [('imx351','liteon_imx351'), ('s5k3h7','chicony_s5k3h7')]:
    data = (base / f'com.qti.sensormodule.{module}.bin').read_bytes()
    assert data.startswith(b'QTI Chromatix Header')
    sb, ss = struct.unpack_from('<QQ', data, 168)
    db, ds = struct.unpack_from('<QQ', data, 192)
    assert ss % 72 == 0 and db + ds <= len(data)
    syms = {}
    for off in range(sb, sb + ss, 72):
        ident, name, version, mode, start, size = struct.unpack_from('<Q32sQQQQ', data, off)
        assert start + size <= ds and size % 8 == 0
        syms[ident] = {'name':name.split(b'\0')[0].decode(), 'values':list(struct.unpack_from('<'+'Q'*(size//8),data,db+start))}
    tables = []
    for ident, sym in syms.items():
        if sym['name'] != 'regSetting':
            continue
        regs = []
        assert len(sym['values']) % 10 == 0
        for start in range(0, len(sym['values']), 10):
            v = sym['values'][start:start+10]
            assert syms[v[4]]['name'] == 'registerData'
            regs.append(dict(address=v[2], data=syms[v[4]]['values'], address_type=v[5], data_type=v[6], operation=v[7], delay_us=syms[v[9]]['values']))
        tables.append({'symbol':ident, 'registers':regs})
    (base / f'{model}-tables.json').write_text(json.dumps({'symbols':syms,'tables':tables}, indent=2)+'\n')
    print(model)
    for ident, sym in syms.items():
        if sym['values'] and sym['name'] not in ('registerData','delayUs','regSetting','slaveAddr') and any(s in sym['name'].lower() for s in ('sensor', 'power', 'actuator', 'resolution', 'module', 'output')):
            print(ident, sym['name'], sym['values'][:100])
    print('tables', [(t['symbol'],len(t['registers'])) for t in tables])
