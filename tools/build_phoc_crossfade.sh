#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
sysroot=/var/tmp/aura-kali-rootfs
test "$(sha256sum "$project/sources/phoc_0.58~alpha1.orig.tar.xz" | cut -d ' ' -f1)" = 910364cc7ac12f7f15fa300306c14072c4fc247d769b176f4934a934052989a1
patch -d "$sysroot/var/tmp/aura-phoc-source" -p1 --dry-run --reverse < "$sysroot/var/tmp/aura-phoc-source/debian/patches/Apply-upstream-patches.patch" >/dev/null
python3 "$project/tools/patch_phoc_crossfade.py"
chroot "$sysroot" meson compile -C /var/tmp/aura-phoc-build -j 4
mkdir -p "$project/build/kali/phoc-crossfade"
cp "$sysroot/var/tmp/aura-phoc-build/src/phoc" "$project/build/kali/phoc-crossfade/phoc"
aarch64-linux-gnu-strip --strip-debug "$project/build/kali/phoc-crossfade/phoc"
cd "$project/build/kali/phoc-crossfade"
sha256sum phoc > phoc.sha256
cat phoc.sha256
