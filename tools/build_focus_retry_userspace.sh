#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
g++ -std=c++17 -O2 "$project/tests/focus-scene-test.cpp" -o /tmp/aura-focus-scene-test
/tmp/aura-focus-scene-test
python3 "$project/tools/patch_camera_focus_retry.py"
chroot "$root" meson compile -C /var/tmp/aura-libcamera-build -j 12
chroot "$root" meson install -C /var/tmp/aura-libcamera-build --destdir /var/tmp/aura-libcamera-focus-retry-stage
tar -C "$root/var/tmp/aura-libcamera-focus-retry-stage" -czf "$project/build/kali/camera/aura-libcamera-focus-retry-trial.tar.gz" opt
sha256sum "$project/build/kali/camera/aura-libcamera-focus-retry-trial.tar.gz"
