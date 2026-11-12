#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
python3 "$project/tools/patch_nfc_board_config.py"
make -C /var/tmp/aura-mainline-6.18.2/linux O=/var/tmp/aura-mainline-6.18.2/out ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 modules
cp /var/tmp/aura-mainline-6.18.2/out/drivers/nfc/nxp-nci/nxp-nci.ko "$project/build/kali/nfc-screen-state/"
aarch64-linux-gnu-strip --strip-debug "$project/build/kali/nfc-screen-state/nxp-nci.ko"
zstd -q -f "$project/build/kali/nfc-screen-state/nxp-nci.ko"
sha256sum "$project/build/kali/nfc-screen-state/nxp-nci.ko.zst"
