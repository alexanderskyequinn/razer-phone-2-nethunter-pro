#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
source_dir=/var/tmp/aura-mainline-6.18.2/linux
output_dir=/var/tmp/aura-mainline-6.18.2/out
test "$(git -c safe.directory="$source_dir" -C "$source_dir" rev-parse HEAD)" = a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0
cp "$project_dir/port/"sdm845-razer-aura*.dts* "$source_dir/arch/arm64/boot/dts/qcom/"
make -C "$source_dir" O="$output_dir" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- qcom/sdm845-razer-aura.dtb
cp "$output_dir/arch/arm64/boot/dts/qcom/sdm845-razer-aura.dtb" "$project_dir/build/mainline/"
sh -n "$project_dir/diagnostic/mainline-init"
