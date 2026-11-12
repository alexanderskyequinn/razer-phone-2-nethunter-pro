#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
output=/var/tmp/aura-mainline-6.18.2/out
test "$(git -C "$source" rev-parse HEAD)" = a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0
python3 "$project/tools/patch_display_irq_lifetime.py"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image.gz
destination="$project/build/mainline-display-fix"
mkdir -p "$destination"
cp "$output/arch/arm64/boot/Image.gz" "$destination/"
cp "$project/build/mainline/sdm845-razer-aura.dtb" "$destination/"
cp "$output/.config" "$destination/kernel.config"
sha256sum "$destination/Image.gz" "$destination/sdm845-razer-aura.dtb"
