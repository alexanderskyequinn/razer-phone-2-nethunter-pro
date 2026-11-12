#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
module=/var/tmp/aura-camera-startup-module
mkdir -p "$module" "$project/build/kali/camera-startup"
cp "$project/port/aura-camera/Makefile" "$project/port/aura-camera/imx363.c" "$module/"
make -C /var/tmp/aura-mainline-6.18.2/linux O=/var/tmp/aura-mainline-6.18.2/out ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- M="$module" -j4 modules
install -m 644 "$module/imx363.ko" "$project/build/kali/camera-startup/imx363.ko"
aarch64-linux-gnu-strip --strip-debug "$project/build/kali/camera-startup/imx363.ko"
sha256sum "$project/build/kali/camera-startup/imx363.ko"
