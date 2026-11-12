#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
python3 "$project/tools/patch_nfc_cold_irq.py"
source=/var/tmp/aura-mainline-6.18.2/linux
out=/var/tmp/aura-mainline-6.18.2/out
make -C "$source" O="$out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 modules
mkdir -p "$project/build/kali/nfc-cold-irq"
cp "$out/drivers/nfc/nxp-nci/nxp-nci_i2c.ko" "$project/build/kali/nfc-cold-irq/"
aarch64-linux-gnu-strip --strip-debug "$project/build/kali/nfc-cold-irq/nxp-nci_i2c.ko"
zstd -q -f "$project/build/kali/nfc-cold-irq/nxp-nci_i2c.ko"
sha256sum "$project/build/kali/nfc-cold-irq/nxp-nci_i2c.ko.zst"
