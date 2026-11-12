"""Prepare the NFC candidate without touching the phone or the v10 image."""
import hashlib
import json
import shutil
import tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
build=root/'build/kali'
snapshot=root/'test-runs/kali-trial-v10/artifacts/packaged'
snapshot.mkdir(parents=True,exist_ok=True)
manifest=json.loads((build/'boot-manifest-v10.json').read_text())
for name,info in manifest['files'].items():
    if name.endswith('.img'):
        continue
    path=build/name
    target=snapshot/name
    if not target.exists():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==info['sha256'],name
        shutil.copy2(path,target)
for name in ('pack_kali_boot.py','run_kali_boot_update.py','monitor_kali_trial.py'):
    path=root/'tools'/name
    text=path.read_text()
    text=text.replace("'v9', 'v10')", "'v9', 'v10', 'v11')")
    text=text.replace("'v9', 'v10']", "'v9', 'v10', 'v11']")
    path.write_text(text)
with tarfile.open(build/'nfc-modules-v11.tar','w') as archive:
    for path in sorted((build/'nfc-v11/modules').glob('*.ko.zst')):
        archive.add(path,arcname='lib/modules/6.18.2-aura-bringup1+/kernel/drivers/nfc/nxp-nci/'+path.name)
