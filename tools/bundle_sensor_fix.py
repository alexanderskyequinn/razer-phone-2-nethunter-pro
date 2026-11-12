"""Archive the local SSC startup fix separately from firmware and kernel images."""
import hashlib
import io
import json
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
overlay = root / 'port/kali-overlay'
binary = root / 'build/kali/sensor-proxy/iio-sensor-proxy'
assert hashlib.sha256(binary.read_bytes()).hexdigest() == '2b463b420f69df81d43db795ce88caf12682909f165fe16b4168c4f098d87f89'
files = {'usr/local/libexec/aura-iio-sensor-proxy': (binary.read_bytes(), 0o755)}
for relative in ('etc/udev/rules.d/79-aura-sensors.rules',
                 'etc/systemd/system/iio-sensor-proxy.service.d/20-aura-startup.conf'):
    files[relative] = ((overlay / relative).read_bytes().replace(b'\r\n', b'\n'), 0o644)
output = root / 'build/kali/sensor-startup-fix.tar'
with tarfile.open(output, 'w') as archive:
    for name, (data, mode) in files.items():
        info = tarfile.TarInfo(name)
        info.size, info.mode = len(data), mode
        info.uname = info.gname = 'root'
        archive.addfile(info, io.BytesIO(data))
manifest = {
    'source': 'iio-sensor-proxy 3.9 Debian original archive',
    'source_sha256': hashlib.sha256((root / 'sources/archives/iio-sensor-proxy_3.9.orig.tar.bz2').read_bytes()).hexdigest(),
    'patch': 'port/iio-sensor-proxy-ssc-startup.patch',
    'build': 'tools/patch_sensor_startup.py; tools/build_sensor_proxy.sh',
    'verification': 'Upstream orientation and mounting-matrix tests pass. Installed binary hash confirmed; Phosh automatically discovers and claims accelerometer after service restart. User confirms correct portrait and landscape directions after v11 reboot. Brief black screen during rotation remains a display/compositor issue.',
    'rollback': 'Remove /etc/systemd/system/iio-sensor-proxy.service.d/20-aura-startup.conf, reload systemd and restart iio-sensor-proxy to restore the untouched distribution binary. Revert mounting rule separately if required.',
    'files': {name: hashlib.sha256(data).hexdigest() for name, (data, _) in files.items()},
    'archive_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
}
output.with_suffix('.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(output)
