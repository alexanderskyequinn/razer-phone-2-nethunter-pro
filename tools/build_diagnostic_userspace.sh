#!/bin/bash
# Build on Linux; all device-facing binaries are static AArch64/musl.
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
build_dir=${1:-}
if [[ -z "$build_dir" ]]; then
    build_dir=$(mktemp -d /var/tmp/aura-userspace.XXXXXXXX)
elif [[ "$build_dir" != /var/tmp/aura-userspace.* || ! -d "$build_dir" ]]; then
    echo 'Invalid existing build directory' >&2
    exit 1
fi
mkdir -p "$project_dir/build/diagnostic"
printf '%s\n' "$build_dir" > "$project_dir/build/diagnostic/linux-build-directory.txt"
exec 3>&1
exec > "$project_dir/build/diagnostic/userspace-build.log" 2>&1
tar -xf "$project_dir/sources/archives/musl-1.2.5.tar.gz" -C "$build_dir"
tar -xf "$project_dir/sources/archives/busybox-1.37.0.tar.bz2" -C "$build_dir"
cd "$build_dir/musl-1.2.5"
CC=aarch64-linux-gnu-gcc CFLAGS='-O2 -std=gnu99' ./configure --target=aarch64-linux-gnu --prefix="$build_dir/musl" --disable-shared
make -j8
make install
for headers in linux asm asm-generic mtd; do
    ln -sfn "/usr/aarch64-linux-gnu/include/$headers" "$build_dir/musl/include/$headers"
done
cd "$build_dir/busybox-1.37.0"
make defconfig >/dev/null
python3 - <<'PY'
from pathlib import Path
p=Path('.config')
s=p.read_text().replace('# CONFIG_STATIC is not set', 'CONFIG_STATIC=y').replace('CONFIG_TC=y', '# CONFIG_TC is not set')
for key in ('SHA1_HWACCEL', 'SHA256_HWACCEL'):
    s=s.replace(f'CONFIG_{key}=y', f'# CONFIG_{key} is not set')
p.write_text(s)
PY
make oldconfig </dev/null >/dev/null
make -j8 CROSS_COMPILE=aarch64-linux-gnu- CC="$build_dir/musl/bin/musl-gcc" EXTRA_CFLAGS='-std=gnu17'
aarch64-linux-gnu-readelf -h busybox
if aarch64-linux-gnu-readelf -l busybox | grep -q INTERP; then
    echo 'ERROR: dynamically linked binary is unsuitable for this ramdisk' >&2
    exit 1
fi
cp busybox "$project_dir/build/diagnostic/busybox"
cp .config "$project_dir/build/diagnostic/busybox.config"
sha256sum busybox
echo 'Static AArch64 BusyBox built; see build/diagnostic/userspace-build.log.' >&3
