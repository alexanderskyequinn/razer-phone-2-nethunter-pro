#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
sysroot=/var/tmp/aura-kali-rootfs
source="$sysroot/var/tmp/aura-phoc-source"
test "$(sha256sum "$project/sources/phoc_0.58~alpha1.orig.tar.xz" | cut -d ' ' -f1)" = 910364cc7ac12f7f15fa300306c14072c4fc247d769b176f4934a934052989a1
test "$(sha256sum "$project/sources/phoc_0.58~alpha1-1.debian.tar.xz" | cut -d ' ' -f1)" = 35d69d0fac7bcfed18a2ee81e79b67ce7c0d1c39ca62fbd3a00ba9bcef98dda0
if patch -d "$source" -p1 --dry-run --forward < "$source/debian/patches/Apply-upstream-patches.patch" >/dev/null; then
    patch -d "$source" -p1 < "$source/debian/patches/Apply-upstream-patches.patch"
else
    patch -d "$source" -p1 --dry-run --reverse < "$source/debian/patches/Apply-upstream-patches.patch" >/dev/null
fi
python3 "$project/tools/patch_phoc_rotation.py"
chroot "$sysroot" meson setup /var/tmp/aura-phoc-build /var/tmp/aura-phoc-source --prefix=/usr --default-library=static -Dembed-wlroots=enabled -Dtests=true -Dman=false -Dgtk_doc=false --wrap-mode=nodownload
chroot "$sysroot" meson compile -C /var/tmp/aura-phoc-build -j 4
mkdir -p "$project/build/kali/phoc-live-rotation"
cp "$sysroot/var/tmp/aura-phoc-build/src/phoc" "$project/build/kali/phoc-live-rotation/phoc"
aarch64-linux-gnu-strip --strip-debug "$project/build/kali/phoc-live-rotation/phoc"
sha256sum "$project/build/kali/phoc-live-rotation/phoc"
