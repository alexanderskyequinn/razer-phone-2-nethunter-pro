#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-kali-rootfs/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa
if grep -q 'AURA bounded contrast autofocus' "$source/src/libcamera/pipeline/simple/simple.cpp"; then
  patch -d "$source" -p1 -R < "$project/port/libcamera-aura-autofocus.patch"
fi
python3 "$project/tools/patch_camera_autofocus.py"
chroot /var/tmp/aura-kali-rootfs meson compile -C /var/tmp/aura-libcamera-build -j 12
