"""Export only the retained Razer full-resolution IMX351 register tables."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
data = json.loads((root/'device-data/camera-reference/imx351-tables.json').read_text())
lines = ['/* Generated from retained liteon_imx351 module, symbols 2705 and 21. */']
for ident, name, count in [(2705, 'imx351_global', 150), (21, 'imx351_full', 95)]:
    table = next(t for t in data['tables'] if t['symbol'] == ident)['registers']
    assert len(table) == count
    lines.append('static const struct cci_reg_sequence '+name+'[] = {')
    for r in table:
        assert r['address_type'] == 2 and r['data_type'] == 1 and r['operation'] == 0
        assert len(r['data']) == 1 and r['delay_us'] == [0]
        assert r['address'] not in (0x0100, 0x0103)  # Stream/reset handled explicitly.
        lines.append(f'    {{ CCI_REG8(0x{r["address"]:04x}), 0x{r["data"][0]:02x} }},')
    lines.append('};')
out = root/'port/aura-telecamera/imx351_tables.h'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text('\n'.join(lines)+'\n')
print(out)
