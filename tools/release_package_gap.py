from pathlib import Path
import json
import subprocess
project=Path(__file__).resolve().parents[1]
root=Path('/var/tmp/aura-kali-release-rootfs')
actual=subprocess.check_output(['chroot',str(root),'dpkg-query','-W','-f=${binary:Package}\t${Version}\n'],text=True)
def parse(text):
    return dict(line.split('\t',1) for line in text.splitlines() if '\t' in line)
base=parse(actual)
phone=parse((project/'test-runs/snapshot/release-inventory.txt').read_text().split('RUNTIME FILE NAMES ONLY')[0])
needed={p.split(':')[0]:v for p,v in phone.items() if p not in base or base[p]!=v}
cache={}
files=list((project/'build/kali').rglob('*.deb'))+list(Path('/var/tmp/aura-kali-build/radio-debs').glob('*.deb'))
for f in files:
    info=subprocess.check_output(['dpkg-deb','-f',str(f),'Package','Version'],text=True).splitlines()
    values=dict(x.split(': ',1) for x in info)
    if values['Package'] in needed and values['Version']==needed[values['Package']]:
        cache[values['Package']]=str(f)
out={'needed':needed,'cached':cache,'missing':[p for p in needed if p not in cache]}
(project/'build/kali/release/package-gap.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
