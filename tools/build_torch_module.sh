#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
output=/var/tmp/aura-mainline-6.18.2/out
module=/var/tmp/aura-torch-module
mkdir -p "$module" "$project/build/kali/torch"
cp "$project/port/aura-torch/Makefile" "$project/port/aura-torch/leds-aura-lm3644.c" "$module/"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- M="$module" -j4 modules
install -m 644 "$module/leds-aura-lm3644.ko" "$project/build/kali/torch/"
aarch64-linux-gnu-strip --strip-debug "$project/build/kali/torch/leds-aura-lm3644.ko"
modinfo "$project/build/kali/torch/leds-aura-lm3644.ko" | grep -E 'filename:|vermagic:|depends:'
bash "$project/tools/build_mainline_dtb.sh"
sha256sum "$project/build/kali/torch/leds-aura-lm3644.ko"
