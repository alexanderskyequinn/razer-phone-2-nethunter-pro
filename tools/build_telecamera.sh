#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
output=/var/tmp/aura-mainline-6.18.2/out
module=/var/tmp/aura-telecamera-module
target="$project/build/kali/telecamera"
mkdir -p "$module" "$target"
cp "$project/port/aura-telecamera/"* "$module/"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ M="$module" -j4 modules
install -m 0644 "$module/imx351.ko" "$target/"
aarch64-linux-gnu-strip --strip-debug "$target/imx351.ko"
cp "$project/port/"sdm845-razer-aura*.dts* "$source/arch/arm64/boot/dts/qcom/"
printf '#include "sdm845-razer-aura.dts"\n#include "sdm845-razer-aura-camera-probe.dtsi"\n#include "sdm845-razer-aura-telecamera.dtsi"\n' > "$source/arch/arm64/boot/dts/qcom/sdm845-razer-aura-tele.dts"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ qcom/sdm845-razer-aura-tele.dtb
cp "$output/arch/arm64/boot/dts/qcom/sdm845-razer-aura-tele.dtb" "$target/sdm845-razer-aura.dtb"
cp "$project/build/kali/panel-wake-kernel/Image.gz" "$target/"
modinfo "$target/imx351.ko" | grep -E 'vermagic|depends'
sha256sum "$target/"*
