"""Decode and round-trip the active panel's captured Qualcomm command streams."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / 'port/live-panel-reference.json'
panel = json.loads(source.read_text())
timing = next(v for k, v in panel['panel_tree'].items() if k.endswith('/timing@0'))
records = {}
for phase in ('on', 'off'):
    original = bytes.fromhex(timing['qcom,mdss-dsi-' + phase + '-command'])
    commands = []
    offset = 0
    rebuilt = bytearray()
    while offset < len(original):
        header = original[offset:offset + 7]
        assert len(header) == 7
        dtype, last, channel, ack, delay, high, low = header
        size = high * 256 + low
        payload = original[offset + 7:offset + 7 + size]
        assert len(payload) == size and 0 < size <= 64
        assert dtype in (0x05, 0x15, 0x39, 0x29) and channel == 0 and ack == 0
        assert last == 1
        commands.append({'type': dtype, 'delay_ms': delay, 'payload': payload.hex()})
        rebuilt += header + payload
        offset += 7 + size
    assert rebuilt == original
    records[phase] = {'sha256': hashlib.sha256(original).hexdigest(), 'commands': commands}
lines = ['/* SPDX-License-Identifier: GPL-2.0-only */',
         '/* Generated from the Razer live DT; see panel-command-validation.json. */',
         'struct aura_panel_cmd { u8 type, delay_ms, length; u8 data[64]; };']
for phase, record in records.items():
    lines.append('static const struct aura_panel_cmd aura_' + phase + '[] = {')
    for cmd in record['commands']:
        data = bytes.fromhex(cmd['payload'])
        lines.append('\t{0x%02x, %d, %d, {%s}},' % (cmd['type'], cmd['delay_ms'], len(data), ', '.join('0x%02x' % b for b in data)))
    lines.append('};')
(root / 'port/panel-razer-nt36830-commands.h').write_text('\n'.join(lines) + '\n')
(root / 'port/panel-command-validation.json').write_text(json.dumps(records, indent=2) + '\n')
print({k: len(v['commands']) for k, v in records.items()})
