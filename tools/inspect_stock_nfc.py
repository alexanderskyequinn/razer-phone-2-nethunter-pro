"""Extract and summarize the captured Razer NFC configuration, without device writes."""
import hashlib
import json
import re
import tarfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]
out = root / 'device-data/native-prerequisites/nfc-stock-config'
out.mkdir(exist_ok=True)
with tarfile.open(root / 'device-data/native-prerequisites/aura-nfc-stock-config.tar') as archive:
    for name in ('libnfc-nxp.conf', 'libnfc-nci.conf'):
        data = archive.extractfile('nfc-stock-config/' + name).read()
        (out / name).write_bytes(data)
        reference = root / 'sources/android_device_razer_aura/nfc' / name
        print(name, 'SHA256', hashlib.sha256(data).hexdigest(), 'matches Lineage:', data.replace(b'\r\n', b'\n') == reference.read_bytes().replace(b'\r\n', b'\n'))
text = re.sub(r'#[^\n]*', '', (out / 'libnfc-nxp.conf').read_text())
commands = {}
for name, raw in re.findall(r'(\w+)\s*=\s*\{([^}]*)\}', text):
    values = bytes(int(x.strip(), 16) for x in re.split('[,:]', raw) if x.strip())
    commands[name] = values.hex()
    if name.startswith(('NXP_RF_CONF',)):
        print(name, len(values), 'bytes')
    else:
        print(name, values.hex())
(out / 'command-blocks.json').write_text(json.dumps(commands, indent=2) + '\n')
