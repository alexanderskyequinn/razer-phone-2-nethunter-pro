#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
output=/var/tmp/aura-mainline-6.18.2/out
module=/var/tmp/aura-telefocus-module
target="$project/build/kali/telefocus"
mkdir -p "$module" "$target"
cp "$project/port/aura-telefocus/"* "$module/"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ M="$module" -j4 modules
install -m 0644 "$module/lc898217.ko" "$target/"
aarch64-linux-gnu-strip --strip-debug "$target/lc898217.ko"
cp "$project/port/"sdm845-razer-aura*.dts* "$source/arch/arm64/boot/dts/qcom/"
printf '#include "sdm845-razer-aura.dts"\n#include "sdm845-razer-aura-camera-probe.dtsi"\n#include "sdm845-razer-aura-telecamera.dtsi"\n#include "sdm845-razer-aura-telefocus.dtsi"\n' > "$source/arch/arm64/boot/dts/qcom/sdm845-razer-aura-telefocus.dts"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ qcom/sdm845-razer-aura-telefocus.dtb
cp "$output/arch/arm64/boot/dts/qcom/sdm845-razer-aura-telefocus.dtb" "$target/sdm845-razer-aura.dtb"
cp "$project/build/kali/panel-wake-kernel/Image.gz" "$target/"
modinfo "$target/lc898217.ko" | grep -E 'vermagic|depends'
sha256sum "$target/"*
