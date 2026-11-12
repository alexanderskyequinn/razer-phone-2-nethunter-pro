#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
out=/var/tmp/aura-mainline-6.18.2/out
mkdir -p "$project/test-runs/kali-trial-v9/artifacts"
cp "$project/build/mainline/sdm845-razer-aura.dtb" "$project/test-runs/kali-trial-v9/artifacts/"
cp "$project/port/"sdm845-razer-aura*.dts* "$source/arch/arm64/boot/dts/qcom/"
python3 "$project/tools/install_radio_audio_fixes.py" "$source"
make -C "$source" O="$out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 modules qcom/sdm845-razer-aura.dtb
cp "$out/arch/arm64/boot/dts/qcom/sdm845-razer-aura.dtb" "$project/build/mainline/"
bash "$project/tools/stage_peripheral_modules.sh"
