#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
out="$project/build/kali/telephony-packages"
test -f "$root/etc/aura-install-id"
backup=$(mktemp -d)
cp -a "$root/etc/resolv.conf" "$backup/resolv.conf"
restore() { cp -a --remove-destination "$backup/resolv.conf" "$root/etc/resolv.conf"; rm -f "$backup/resolv.conf"; rmdir "$backup"; }
trap restore EXIT
cp --remove-destination -L /etc/resolv.conf "$root/etc/resolv.conf"
mkdir -p "$root/var/tmp/aura-telephony-debs/partial" "$out"
chroot "$root" apt-get -y --download-only --no-install-recommends -o Dir::Cache::archives=/var/tmp/aura-telephony-debs install 81voltd gnome-calls chatty
cp "$root"/var/tmp/aura-telephony-debs/*.deb "$out/"
cd "$out"
sha256sum ./*.deb > SHA256SUMS
tar -cf ../telephony-packages.tar ./*.deb SHA256SUMS
mkdir -p /var/tmp/aura-81voltd-inspect
dpkg-deb -x ./81voltd_1.2.0-2_arm64.deb /var/tmp/aura-81voltd-inspect
find /var/tmp/aura-81voltd-inspect/usr/share/doc/81voltd -type f -maxdepth 1 -print
