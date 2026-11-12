#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
source=/var/tmp/aura-mainline-6.18.2/linux
output=/var/tmp/aura-mainline-6.18.2/out
patchfile="$project/port/nci-upstream-packet-validation.patch"
if git -C "$source" apply --reverse --check "$patchfile" 2>/dev/null; then
    echo 'Upstream NFC parser correction already applied.'
else
    git -C "$source" apply --check "$patchfile"
    git -C "$source" apply "$patchfile"
fi
grep '^CONFIG_NFC_NCI=m$' "$output/.config"
make -C "$source" O="$output" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j8 modules
destination="$project/build/kali/nci-parser-fix"
mkdir -p "$destination"
cp "$output/net/nfc/nci/nci.ko" "$destination/nci.ko"
aarch64-linux-gnu-strip --strip-debug "$destination/nci.ko"
zstd -q -f "$destination/nci.ko"
sha256sum "$destination/nci.ko.zst"
