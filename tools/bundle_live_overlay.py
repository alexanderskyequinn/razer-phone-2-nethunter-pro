import tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
overlay=root/'port/kali-overlay'
paths=['usr/share/alsa/ucm2']
with tarfile.open(root/'build/kali/live-hardware-overlay.tar','w') as tar:
    for name in paths:
        path=overlay/name
        for item in sorted(path.rglob('*')) if path.is_dir() else [path]:
            if item.is_file():
                info=tar.gettarinfo(str(item),arcname=item.relative_to(overlay).as_posix())
                info.mode=0o755 if 'sbin/' in info.name else 0o644
                with item.open('rb') as f: tar.addfile(info,f)
