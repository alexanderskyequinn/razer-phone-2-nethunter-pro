#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
export DEBIAN_FRONTEND=noninteractive
chroot "$root" apt-get -y --download-only --no-install-recommends install glmark2-es2-wayland
cd "$root/var/cache/apt/archives"
tar -cf "$project_dir/build/kali/gpu-benchmark-debs.tar" ./*.deb
