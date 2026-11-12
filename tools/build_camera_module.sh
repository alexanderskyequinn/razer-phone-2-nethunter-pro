#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
output=/var/tmp/aura-mainline-6.18.2/out
module=/var/tmp/aura-camera-module
mkdir -p "$module" "$project/build/kali/camera"
cp "$project/port/aura-camera/Makefile" "$project/port/aura-camera/imx363.c" "$module/"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- M="$module" -j4 modules
install -m 644 "$module/imx363.ko" "$project/build/kali/camera/"
aarch64-linux-gnu-strip --strip-debug "$project/build/kali/camera/imx363.ko"
modinfo "$project/build/kali/camera/imx363.ko" | grep -E 'filename:|vermagic:|depends:'
bash "$project/tools/build_mainline_dtb.sh"
