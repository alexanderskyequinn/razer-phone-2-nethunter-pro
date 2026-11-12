#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-qseecom-6.18.2/linux
output=/var/tmp/aura-qseecom-6.18.2/out
mkdir -p "$output"
if [ ! -f "$output/.config" ]; then
    cp /var/tmp/aura-mainline-6.18.2/out/.config "$output/.config"
    "$source/scripts/config" --file "$output/.config" --enable TEE_QSEECOM
fi
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ olddefconfig
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LOCALVERSION=+ W=1 -j4 drivers/tee/qseecom/core.o drivers/firmware/qcom/qcom_scm.o drivers/soc/qcom/mdt_loader.o
