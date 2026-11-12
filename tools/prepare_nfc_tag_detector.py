"""Add only captured tag-detector/field parameters to the screen-state setup."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / 'device-data/native-prerequisites/nfc-stock-config'
assert hashlib.sha256((source/'libnfc-nxp.conf').read_bytes()).hexdigest() == 'cf69b6d8eb0374b3684f1f2b5a19a860cc8b636982d0f8e30f9001e0b757a1aa'
commands = json.loads((source/'command-blocks.json').read_text())
data = bytes.fromhex(commands['NXP_CORE_CONF_EXTN'])
assert len(data) == data[2] + 3
pos = 4
selected = []
names = []
for _ in range(data[3]):
    start = pos
    assert data[pos] == 0xa0
    key = data[pos:pos+2]
    pos += 2
    size = data[pos]
    pos += 1 + size
    if key in (bytes.fromhex('a040'), bytes.fromhex('a043'), bytes.fromhex('a038'), bytes.fromhex('a03a')):
        selected.append(data[start:pos])
        names.append(key.hex())
assert pos == len(data)
assert len(selected) == 4
body = bytes([len(selected)]) + b''.join(selected)
extra = b'\x20\x02' + bytes([len(body)]) + body
base = (root/'build/kali/nfc-screen-state/razer-aura-nci-config.bin').read_bytes()
assert hashlib.sha256(base).hexdigest() == 'be86e86d8266225ef80f98b3e2b0c370b5d6f7b84535e4ab9d9c97f3375283cf'
assert base[-4:] == bytes.fromhex('2f150100')
payload = base[:-4] + extra + base[-4:]
out = root/'build/kali/nfc-tag-detector'
out.mkdir(exist_ok=True)
(out/'razer-aura-nci-config.bin').write_bytes(payload)
manifest = {'base_sha256': hashlib.sha256(base).hexdigest(), 'added_original_parameters': names,
            'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload),
            'scope': 'Original tag detector and RF field parameters only; other CORE_CONF_EXTN parameters excluded.',
            'verification': 'Prepared only, not installed.'}
(out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps(manifest, indent=2))
