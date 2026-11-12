"""Package the isolated compositor test and its exact configuration."""
import hashlib
import json
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
build = root/'build/kali/phoc-live-rotation'
assert hashlib.sha256((build/'phoc').read_bytes()).hexdigest() == 'ccfb6e64234feb22a9e5a58f044783bcd91b70670ea758883b3ae35ab623e48b'
config = '[Service]\nEnvironment=PHOC_AURA_LIVE_ROTATION=1\nExecStart=\nExecStart=capsh --noamb -- -c "exec /usr/local/libexec/aura-phosh-session"\n'
(build/'30-aura-live-rotation.conf').write_text(config)
files = [('phoc', 'usr/local/libexec/aura-phoc', 0o755), ('aura-phosh-session', 'usr/local/libexec/aura-phosh-session', 0o755), ('30-aura-live-rotation.conf', 'etc/systemd/system/phosh.service.d/30-aura-live-rotation.conf', 0o644)]
archive_path = build.with_suffix('.tar')
with tarfile.open(archive_path, 'w') as archive:
    for source, destination, mode in files:
        path = build/source
        info = archive.gettarinfo(str(path), arcname=destination)
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        info.mode = mode
        with path.open('rb') as stream:
            archive.addfile(info, stream)
manifest = {
    'source_package': 'phoc 0.58~alpha1-1, same version as packaged desktop',
    'upstream_tar_sha256': '910364cc7ac12f7f15fa300306c14072c4fc247d769b176f4934a934052989a1',
    'distribution_patch_tar_sha256': '35d69d0fac7bcfed18a2ee81e79b67ce7c0d1c39ca62fbd3a00ba9bcef98dda0',
    'local_patch': 'port/phoc-live-rotation.patch',
    'files': [{'path': dst, 'sha256': hashlib.sha256((build/src).read_bytes()).hexdigest()} for src, dst, _ in files],
    'archive_sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    'behavior': 'With PHOC_AURA_LIVE_ROTATION=1, transform commits do not raise a new black layout shield. Existing startup/lock shields and transaction accounting unchanged. Client resize may remain visible.',
    'validation': 'outputs-states, layer-shell and timed-animation tests pass. User reports improved pause, occasional ~100ms black flash, and transient half-screen layout that corrects quickly. This candidate is not a complete visual fix.',
    'installed_state': 'Superseded in the temporary runtime service override by the retained-frame crossfade candidate. Binary and launcher remain available for rollback; packaged /usr/bin/phoc unchanged. Archive contains a persistent equivalent that was never activated persistently.',
    'rollback': 'Remove only the 30-aura-live-rotation.conf override, daemon-reload and restart phosh. Original packaged phoc SHA256 9f5d306cc1bb535a3663aeaaba4189e3ea4fa6c41c3f4588cf5ad74c3d2436ef remains installed.',
    'evidence': ['build/kali/phoc-rotation-tests.log', 'test-runs/kali-trial-v12/phoc-live-rotation-running.txt'],
}
build.with_suffix('.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(archive_path)
