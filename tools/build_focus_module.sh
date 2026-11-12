#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
output=/var/tmp/aura-mainline-6.18.2/out
module=/var/tmp/aura-focus-module
mkdir -p "$module" "$project/build/kali/focus"
cp "$project/port/aura-focus/Makefile" "$project/port/aura-focus/bu64753.c" "$module/"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- M="$module" -j4 modules
install -m 644 "$module/bu64753.ko" "$project/build/kali/focus/"
aarch64-linux-gnu-strip --strip-debug "$project/build/kali/focus/bu64753.ko"
modinfo "$project/build/kali/focus/bu64753.ko" | grep -E 'filename:|vermagic:|depends:'
bash "$project/tools/build_mainline_dtb.sh"
