#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
out="$project/build/kali/peripheral-modules"
cd /var/tmp/aura-mainline-6.18.2/out
for module in drivers/input/misc/qcom-spmi-haptics.ko drivers/bluetooth/hci_uart.ko drivers/bluetooth/btqca.ko sound/soc/qcom/snd-soc-sdm845.ko; do
    mkdir -p "$out/$(dirname "$module")"
    cp "$module" "$out/$module"
    aarch64-linux-gnu-strip --strip-debug "$out/$module"
    zstd -q -f "$out/$module"
    modinfo "$out/$module" | grep -E 'filename:|vermagic:'
done
