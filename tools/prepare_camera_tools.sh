#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
test -f "$root/etc/aura-install-id"
mkdir -p "$project/build/kali/camera/packages"
chroot "$root" apt-get -o Acquire::Retries=1 -o Acquire::https::Timeout=20 --download-only install -y --no-install-recommends v4l-utils libcamera-tools
for name in v4l-utils libv4l libcamera liblttng libunwind libdw libelf libyaml; do
    find "$root/var/cache/apt/archives" -maxdepth 1 -name "${name}*.deb" -exec cp -t "$project/build/kali/camera/packages" {} +
done
ls -lh "$project/build/kali/camera/packages"
