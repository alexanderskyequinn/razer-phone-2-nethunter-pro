#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
out=/var/tmp/aura-mainline-6.18.2/out
snapshot="$project/test-runs/kali-trial-v10/artifacts"
mkdir -p "$snapshot"
for item in Image.gz sdm845-razer-aura.dtb kernel.config; do
    test -f "$snapshot/$item" || cp "$project/build/mainline/$item" "$snapshot/$item"
done
cp "$project/port/"sdm845-razer-aura*.dts* "$source/arch/arm64/boot/dts/qcom/"
"$source/scripts/config" --file "$out/.config" -m NFC -m NFC_NCI -m NFC_NXP_NCI -m NFC_NXP_NCI_I2C
make -C "$source" O="$out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -C "$source" O="$out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 Image.gz modules qcom/sdm845-razer-aura.dtb
mkdir -p "$project/build/kali/nfc-v11/modules"
cp "$out/arch/arm64/boot/dts/qcom/sdm845-razer-aura.dtb" "$project/build/kali/nfc-v11/"
cp "$out/.config" "$project/build/kali/nfc-v11/kernel.config"
cp "$out/arch/arm64/boot/Image.gz" "$project/build/kali/nfc-v11/"
for module in drivers/nfc/nxp-nci/nxp-nci.ko drivers/nfc/nxp-nci/nxp-nci_i2c.ko; do
    cp "$out/$module" "$project/build/kali/nfc-v11/modules/"
    aarch64-linux-gnu-strip --strip-debug "$project/build/kali/nfc-v11/modules/$(basename "$module")"
    zstd -q -f "$project/build/kali/nfc-v11/modules/$(basename "$module")"
done
