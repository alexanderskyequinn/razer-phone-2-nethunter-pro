"""Stage this phone's captured wireless firmware without publishing it."""
import hashlib, io, json, re, tarfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
dest = ROOT / 'build/kali/radio-firmware'
dest.mkdir(exist_ok=True)
records = {}
def save(name, data, source):
    p = dest / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    records[name] = dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),source=source)
with tarfile.open(ROOT/'device-data/native-prerequisites/vendor-firmware.tar') as t:
    for m in t.getmembers():
        name=Path(m.name).name
        if m.isfile() and m.name.startswith('firmware_mnt/image/') and (re.fullmatch(r'(modem|adsp|slpi|cdsp)\.(mdt|b[0-9]{2})',name) or name in ('mba.mbn','wlanmdsp.mbn') or name.endswith('.jsn')):
            save('qcom/sdm845/razer/aura/'+name,t.extractfile(m).read(),m.name)
    board=t.extractfile('firmware_mnt/image/bdwlan.bin').read()
    save('ath10k/WCN3990/hw1.0/board.bin',board,'firmware_mnt/image/bdwlan.bin')
with tarfile.open(ROOT/'device-data/native-prerequisites/aura-radio-original.tar') as t:
    blob=t.extractfile('radio-original/bluetooth-firmware.tar').read()
with tarfile.open(fileobj=io.BytesIO(blob)) as t:
    for m in t.getmembers():
        name=Path(m.name).name
        if m.isfile() and name.startswith(('crbtfw','crnv')):
            save(('qca/razer/aura/' if name.startswith('crnv') else 'qca/')+name,t.extractfile(m).read(),'bluetooth_a:'+m.name)
(dest/'manifest.json').write_text(json.dumps(records,indent=2))
with tarfile.open(ROOT/'build/kali/radio-firmware.tar','w') as t:
    for name in records: t.add(dest/name,arcname=name)
print(f'Staged {len(records)} device firmware files; original archives preserved.')
