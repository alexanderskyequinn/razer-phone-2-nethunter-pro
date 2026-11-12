"""Preserve the user-validated crossfade and its persistent configuration."""
import hashlib
import json
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
build = root/'build/kali/phoc-crossfade'
expected = '12c47e799a482fed557a8d671f9cd2b959fadcd19c9fc71a87d95a855486b35d'
assert hashlib.sha256((build/'phoc').read_bytes()).hexdigest() == expected
files = [
    ('build/kali/phoc-crossfade/phoc', 'usr/local/libexec/aura-phoc-crossfade', 0o755),
    ('build/kali/phoc-crossfade/aura-phosh-crossfade-session', 'usr/local/libexec/aura-phosh-crossfade-session', 0o755),
    ('port/kali-overlay/etc/systemd/system/phosh.service.d/30-aura-crossfade.conf', 'etc/systemd/system/phosh.service.d/30-aura-crossfade.conf', 0o644),
    ('port/phoc-rotation-crossfade.patch', 'source/phoc-rotation-crossfade.patch', 0o644),
    ('tests/phoc-test-rotation-crossfade.c', 'source/test-rotation-crossfade.c', 0o644),
]
archive_path = build.with_suffix('.tar')
with tarfile.open(archive_path, 'w') as archive:
    for source, destination, mode in files:
        path = root/source
        info = archive.gettarinfo(str(path), arcname=destination)
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        info.mode = mode
        with path.open('rb') as stream:
            archive.addfile(info, stream)
manifest = {
    'source_package': 'phoc 0.58~alpha1-1 with original Debian wlroots patches',
    'binary_sha256': expected,
    'archive_sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    'patch': 'port/phoc-rotation-crossfade.patch',
    'option': 'PHOC_AURA_ROTATION_CROSSFADE=1',
    'behavior': 'Retain one composed physical frame in GPU memory. Wait for visible layer and xdg client resize commits, bounded to 300ms, then smoothstep crossfade over 150ms. This is a crossfade, not an animated angular rotation. No screenshots saved on the phone.',
    'lifecycle': 'Mapped overlay surfaces and output shields cancel cached content; overlay rendered after crossfade. Output disable/mode change/finalize clear texture and buffer. Retained buffer stays locked. Direct fullscreen scanout bypassed while option enabled so composed frames are available.',
    'validation': 'Existing outputs-states, layer-shell, timed-animation, xdg-shell tests pass. New actual-render test passes: full retained frame while client resize delayed, complete new frame after fade, overlay immediately covers transition. User confirms crossfade looks good before persistence. Reboot a7517520-8076-4a4b-8de7-dd5ce9acce16 verified the exact custom binary, persistent service drop-in and enabled crossfade with GLES2; user accepts post-reboot rotation as good enough, though a little sluggish.',
    'limitations': 'No Android-style spinning animation. Slow/unresponsive clients can exceed the bounded hold. XWayland resize readiness is not tracked individually. Battery/performance impact of retaining one frame and bypassing fullscreen direct scanout not measured.',
    'installed_state': 'Persistent /etc/systemd/system/phosh.service.d/30-aura-crossfade.conf selects separate binary and launcher; former temporary runtime override removed. Packaged compositor preserved. Local image configuration updated.',
    'rollback_to_packaged': 'Remove only /etc/systemd/system/phosh.service.d/30-aura-crossfade.conf, daemon-reload and restart phosh.',
    'evidence': ['build/kali/phoc-crossfade-tests.log', 'build/kali/phoc-crossfade-render-test.log', 'build/kali/phoc-crossfade-render-test-full.log', 'test-runs/kali-trial-v12/crossfade-persistent.txt', 'test-runs/kali-trial-v12/crossfade-reboot-health-final.txt'],
}
build.with_suffix('.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(archive_path)
