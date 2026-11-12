"""Copy/download the exact packages requested by the phone's APT resolver."""
from pathlib import Path
import re
import shutil
import urllib.parse
import urllib.request
root = Path(__file__).resolve().parents[1]
log = (root/'test-runs/kali-trial-v18/camera-tools.txt').read_text()
out = root/'build/kali/camera/offline'
out.mkdir(exist_ok=True)
cache = Path('/var/tmp/aura-kali-rootfs/var/cache/apt/archives')
urls = re.findall(r'^E: Failed to fetch (https://kali.download/kali/\S+)', log, re.M)
assert len(urls) == 32
for url in urls:
    name = urllib.parse.unquote(url.rsplit('/',1)[1])
    if (cache/name).exists():
        shutil.copyfile(cache/name, out/name)
    else:
        urllib.request.urlretrieve(url, out/name)
    print(name, flush=True)
