#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
g++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined -g "$project/tests/focus-timing-test.cpp" -o /var/tmp/aura-focus-timing-test
/var/tmp/aura-focus-timing-test
g++ -std=c++17 -Wall -Wextra -Werror "$project/tests/focus-scene-test.cpp" -o /var/tmp/aura-focus-scene-test
/var/tmp/aura-focus-scene-test
python3 "$project/tools/patch_camera_focus_timing.py"
chroot "$root" meson compile -C /var/tmp/aura-libcamera-build -j 8
chroot "$root" meson install -C /var/tmp/aura-libcamera-build --destdir /var/tmp/aura-libcamera-focus-timing-stage
tar -C "$root/var/tmp/aura-libcamera-focus-timing-stage" -czf "$project/build/kali/camera/aura-libcamera-focus-timing-trial.tar.gz" opt
sha256sum "$project/build/kali/camera/aura-libcamera-focus-timing-trial.tar.gz"
