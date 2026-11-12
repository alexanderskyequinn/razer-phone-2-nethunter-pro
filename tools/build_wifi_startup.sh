#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
python3 "$project/tools/patch_wifi_startup.py"
make -C /var/tmp/aura-mainline-6.18.2/linux O=/var/tmp/aura-mainline-6.18.2/out ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 modules
destination="$project/build/kali/wifi-startup"
mkdir -p "$destination"
cp /var/tmp/aura-mainline-6.18.2/out/drivers/net/wireless/ath/ath10k/ath10k_snoc.ko "$destination/"
aarch64-linux-gnu-strip --strip-debug "$destination/ath10k_snoc.ko"
zstd -q -f "$destination/ath10k_snoc.ko"
sha256sum "$destination/ath10k_snoc.ko.zst"
