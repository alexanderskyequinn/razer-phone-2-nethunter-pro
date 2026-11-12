import tarfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]
with tarfile.open(root/'build/kali/sensor-packages.tar', 'w') as out:
    for path in sorted((root/'build/kali/sensor-packages').glob('*.deb')):
        out.add(path, arcname=path.name)
