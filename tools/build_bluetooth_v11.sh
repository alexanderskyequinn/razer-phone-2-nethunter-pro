#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
out=/var/tmp/aura-mainline-6.18.2/out
python3 "$project/tools/install_radio_audio_fixes.py" "$source"
make -C "$source" O="$out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 modules
bash "$project/tools/stage_peripheral_modules.sh"
