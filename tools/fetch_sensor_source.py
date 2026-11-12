import re, urllib.request, tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
base='https://deb.debian.org/debian/pool/main/i/iio-sensor-proxy/'
index=urllib.request.urlopen(base).read().decode()
names=re.findall(r'href="([^"]*3\.9\.orig\.tar\.[^"]*)"',index)
assert len(names)==1,names
path=root/'sources/archives'/names[0]
urllib.request.urlretrieve(base+names[0],path)
with tarfile.open(path) as tar:
    tar.extractall(root/'sources/iio-sensor-proxy',filter='data')
print(path, path.stat().st_size)
