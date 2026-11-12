#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
output=/var/tmp/aura-mainline-6.18.2/out
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=safe.directory
export GIT_CONFIG_VALUE_0="$source"
test "$(git -C "$source" rev-parse HEAD)" = a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0
python3 "$project/tools/install_charger_fixes.py" "$source"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image.gz
destination="$project/build/mainline-wireless-reporting"
mkdir -p "$destination"
cp "$output/arch/arm64/boot/Image.gz" "$destination/"
cp "$project/build/kali/wireless-probe-kernel/sdm845-razer-aura.dtb" "$destination/"
cp "$output/.config" "$destination/kernel.config"
sha256sum "$destination/Image.gz" "$destination/sdm845-razer-aura.dtb"
