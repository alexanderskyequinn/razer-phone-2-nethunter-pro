#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
output=/var/tmp/aura-mainline-6.18.2/out
module=/var/tmp/aura-fingerprint-resources-module
target="$project/build/kali/fingerprint-resources"
mkdir -p "$module" "$target"
cp "$project/port/aura-fingerprint/"* "$module/"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ M="$module" W=1 -j4 modules
install -m 0644 "$module/aura_fpc_resources.ko" "$target/"
aarch64-linux-gnu-strip --strip-debug "$target/aura_fpc_resources.ko"
# Compile an isolated DT using the existing preprocessed board include path.
# Only a new test target is written; no existing boot image is rebuilt.
cp "$project/port/sdm845-razer-aura-fingerprint.dtsi" "$source/arch/arm64/boot/dts/qcom/"
printf '#include "sdm845-razer-aura.dts"\n#include "sdm845-razer-aura-camera-probe.dtsi"\n#include "sdm845-razer-aura-telecamera.dtsi"\n#include "sdm845-razer-aura-telefocus.dtsi"\n#include "sdm845-razer-aura-fingerprint.dtsi"\n' > "$source/arch/arm64/boot/dts/qcom/sdm845-razer-aura-fingerprint-test.dts"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ qcom/sdm845-razer-aura-fingerprint-test.dtb
cp "$output/arch/arm64/boot/dts/qcom/sdm845-razer-aura-fingerprint-test.dtb" "$target/"
modinfo "$target/aura_fpc_resources.ko" | grep -E 'vermagic|depends|alias'
sha256sum "$target/"*
