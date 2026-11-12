"""Fetch signed-catalog package artifacts on the PC; no package execution."""
from pathlib import Path
import concurrent.futures,hashlib,json,os,re,tarfile,time,urllib.request
root=Path(__file__).resolve().parents[1]
items=json.loads((root/'build/kali/apps-download-manifest.json').read_text())
cache=Path(os.environ.get('AURA_APPS_CACHE',str(root/'build/kali/app-debs')));cache.mkdir(parents=True,exist_ok=True)
def valid(path,item):
    if not path.exists() or path.stat().st_size!=item['bytes']:return False
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()==item['sha256']
def fetch(item):
    name=item['cache_name'];assert re.fullmatch(r'[A-Za-z0-9+.%_~:-]+\.deb',name)
    assert item['url'].startswith('https://kali.download/kali/pool/')
    target=cache/name
    if valid(target,item):return item['bytes']
    part=target.with_suffix('.part')
    for attempt in range(4):
        try:
            with urllib.request.urlopen(item['url'],timeout=45) as response,part.open('wb') as f:
                while chunk:=response.read(1024*1024):f.write(chunk)
            assert valid(part,item),'Package size or SHA-256 mismatch'
            part.replace(target);return item['bytes']
        except Exception:
            if attempt==3:raise
            time.sleep(attempt+1)
done=0;size=0;start=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    for task in concurrent.futures.as_completed([pool.submit(fetch,item) for item in items]):
        size+=task.result();done+=1
        if done%100==0 or done==len(items):print(f'{done}/{len(items)} packages verified; {size/1e6:.0f} MB; {time.monotonic()-start:.0f}s',flush=True)
archive=Path(os.environ.get('AURA_APPS_ARCHIVE',str(root/'build/kali/apps-verified-cache.tar')))
with tarfile.open(archive,'w') as tar:
    for item in items:tar.add(cache/item['cache_name'],arcname=item['cache_name'],recursive=False)
with archive.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
(root/'build/kali/apps-verified-cache.json').write_text(json.dumps({'packages':len(items),'archive_sha256':digest,'bytes':archive.stat().st_size},indent=2)+'\n')
print(f'Archive ready: {archive.stat().st_size} bytes, sha256 {digest}',flush=True)
