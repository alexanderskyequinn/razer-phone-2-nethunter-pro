#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
python3 "$project/tools/patch_modem_nv.py"
make -C /var/tmp/aura-mainline-6.18.2/linux O=/var/tmp/aura-mainline-6.18.2/out ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 modules
destination="$project/build/kali/modem-nv-fix"
mkdir -p "$destination"
cp /var/tmp/aura-mainline-6.18.2/out/drivers/remoteproc/qcom_q6v5_mss.ko "$destination/"
aarch64-linux-gnu-strip --strip-debug "$destination/qcom_q6v5_mss.ko"
zstd -q -f "$destination/qcom_q6v5_mss.ko"
sha256sum "$destination/qcom_q6v5_mss.ko.zst"
