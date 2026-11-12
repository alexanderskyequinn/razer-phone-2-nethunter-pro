#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
chroot "$root" meson install -C /var/tmp/aura-libcamera-build --destdir /var/tmp/aura-libcamera-afstage
tar -C "$root/var/tmp/aura-libcamera-afstage" -czf "$project/build/kali/camera/aura-libcamera-af-trial.tar.gz" opt/aura-camera
sha256sum "$project/build/kali/camera/aura-libcamera-af-trial.tar.gz"
