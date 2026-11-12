#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
output=/var/tmp/aura-mainline-6.18.2/out
test "$(git -c safe.directory="$source" -C "$source" rev-parse HEAD)" = a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0
python3 "$project/tools/install_panel_driver.py" "$source"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ -j8 Image.gz
grep -qx '#define UTS_RELEASE "6.18.2-aura-bringup1+"' "$output/include/generated/utsrelease.h"
candidate="$project/build/kali/panel-wake-kernel"
mkdir -p "$candidate"
cp "$output/arch/arm64/boot/Image.gz" "$candidate/Image.gz"
cp "$project/build/kali/focus-kernel/sdm845-razer-aura.dtb" "$candidate/"
sha256sum "$candidate/"*
