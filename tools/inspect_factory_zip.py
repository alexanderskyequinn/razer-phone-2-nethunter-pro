"""Inspect official ZIP metadata using bounded HTTP ranges; no device writes."""
import io
import urllib.request
import zipfile
from pathlib import Path

URL = 'https://s3.amazonaws.com/cheryl-factory-images/aura-p-release-3201-user-full.zip'
class Remote(io.RawIOBase):
    def __init__(self, offset=0, size=None):
        self.offset=offset
        self.pos=0
        if size is None:
            with urllib.request.urlopen(urllib.request.Request(URL,method='HEAD'),timeout=20) as r:
                size=int(r.headers['Content-Length'])
        self.size=size
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self,n,whence=0):
        self.pos=n if whence==0 else self.pos+n if whence==1 else self.size+n
        if self.pos<0: raise ValueError('negative seek')
        return self.pos
    def read(self,n=-1):
        n=self.size-self.pos if n<0 else min(n,self.size-self.pos)
        if n<=0:return b''
        if n>16*1024*1024:raise ValueError('Oversized metadata request')
        start=self.offset+self.pos
        req=urllib.request.Request(URL,headers={'Range':f'bytes={start}-{start+n-1}'})
        with urllib.request.urlopen(req,timeout=20) as r:
            assert r.status==206, 'Server did not honor Range'
            data=r.read(n+1)
        assert len(data)==n
        self.pos+=n
        return data

if __name__=='__main__':
    import argparse,struct
    p=argparse.ArgumentParser()
    p.add_argument('--extract',help='Exact outer ZIP member to save (max 16 MiB)')
    a=p.parse_args()
    remote=Remote()
    with zipfile.ZipFile(remote) as z:
        for entry in z.infolist():print(entry.filename,entry.file_size,entry.compress_type)
        if a.extract:
            item=z.getinfo(a.extract)
            assert item.file_size<=16*1024*1024
            destination=Path('build/kali/factory-reference')/Path(item.filename).name
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(z.read(item))
            print('Saved',destination)
