#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
python3 "$project/tools/patch_libcamera_telecamera.py"
chroot "$root" meson compile -C /var/tmp/aura-libcamera-build -j 12
chroot "$root" meson install -C /var/tmp/aura-libcamera-build --destdir /var/tmp/aura-libcamera-telestage
tar -C "$root/var/tmp/aura-libcamera-telestage" -czf "$project/build/kali/camera/aura-libcamera-tele-trial.tar.gz" opt
sha256sum "$project/build/kali/camera/aura-libcamera-tele-trial.tar.gz"
