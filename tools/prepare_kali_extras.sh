#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
export DEBIAN_FRONTEND=noninteractive
cp --remove-destination -L /etc/resolv.conf "$root/etc/resolv.conf"
chroot "$root" apt-get -y --download-only --no-install-recommends install \
  iproute2 git qbootctl xwayland at-spi2-core gnome-backgrounds mesa-utils
mkdir -p /var/tmp/aura-kali-build/extras-inspect
for package in "$root"/var/cache/apt/archives/qbootctl_*deb; do
    dpkg-deb -x "$package" /var/tmp/aura-kali-build/extras-inspect
done
cd "$root/var/cache/apt/archives"
tar -cf "$project_dir/build/kali/extras-debs.tar" ./*.deb
echo 'Offline package bundle prepared; phone unchanged.'
