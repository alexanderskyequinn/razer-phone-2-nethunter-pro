#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
out=/var/tmp/aura-mainline-6.18.2/out
test "$(git -c safe.directory="$source" -C "$source" rev-parse HEAD)" = a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0
python3 "$project/tools/patch_logo_supply.py"
# Use the running kernel's configuration and ABI; add only loadable LED modules.
make -C "$source" O="$out" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- CONFIG_LEDS_LP55XX_COMMON=m CONFIG_LEDS_LP5523=m M=drivers/leds -j4 modules
dest="$project/build/kali/logo-modules"
mkdir -p "$dest"
for name in leds-lp55xx-common leds-lp5523 led-class-multicolor; do
 install -m 644 "$source/drivers/leds/$name.ko" "$dest/$name.ko"
 aarch64-linux-gnu-strip --strip-debug "$dest/$name.ko"
 modinfo "$dest/$name.ko" | grep -E 'filename:|vermagic:|depends:'
done
sha256sum "$dest/"*.ko
