#!/bin/bash
set -euo pipefail
: "${AURA_TEST_PIN:?Set your own numeric development PIN}"
[[ "$AURA_TEST_PIN" =~ ^[0-9]{6,64}$ ]] || { echo "PIN must contain 6-64 digits" >&2; exit 1; }
project_dir=$(cd "$(dirname "$0")/.." && pwd)
build_dir=/var/tmp/aura-kali-build
mkdir -p "$build_dir/source" "$build_dir/output" "$build_dir/tmp"
# Build in the Linux filesystem so Unix owners, permissions and links survive.
cp -a "$project_dir/sources/kali-nethunter-pro/." "$build_dir/source/"
python3 - "$build_dir/source" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
for path in root.rglob('*'):
    if not path.is_file() or '.git' in path.parts or path.is_symlink():
        continue
    data = path.read_bytes()
    if b'\x00' in data:
        continue
    try:
        data.decode('utf-8')
    except UnicodeDecodeError:
        continue
    if b'\r\n' in data:
        path.write_bytes(data.replace(b'\r\n', b'\n'))
    if data.startswith(b'#!'):
        path.chmod(path.stat().st_mode | 0o111)
PY
cd "$build_dir/source"
export TMPDIR="$build_dir/tmp"
export DEBIAN_FRONTEND=noninteractive
debos --disable-fakemachine --artifactdir="$build_dir/output" \
  -t suite:forky -t debian_suite:kali-rolling -t architecture:arm64 \
  -t nonfree:true -t contrib:true -t environment:phosh -t ssh:true \
  -t username:kali -t "password:${AURA_TEST_PIN}" -t hostname:kali-aura \
  -t mirror:https://kali.download/kali \
  -t rootfs:rootfs-aura-kali-rolling-arm64.tar.xz rootfs.yaml
sha256sum "$build_dir/output/rootfs-aura-kali-rolling-arm64.tar.xz"
