"""Fetch the pinned upstream Adreno microcode, retaining source and hashes."""
import base64, hashlib, json, struct, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
out = ROOT / 'build/kali/upstream-gpu-firmware'
out.mkdir(exist_ok=True)
base = 'https://kernel.googlesource.com/pub/scm/linux/kernel/git/firmware/linux-firmware/+/refs/tags/20250509/'
records = {}
for name in ('a630_sqe.fw', 'a630_gmu.bin'):
    url = base + 'qcom/' + name + '?format=TEXT'
    data = base64.b64decode(urllib.request.urlopen(url, timeout=40).read(), validate=True)
    assert 4096 < len(data) < 1048576
    (out / name).write_bytes(data)
    records[name] = dict(url=url, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), first_words=struct.unpack_from('<4I', data))
(out / 'manifest.json').write_text(json.dumps(records, indent=2))
print(json.dumps(records, indent=2))
