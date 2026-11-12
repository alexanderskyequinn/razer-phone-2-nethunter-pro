#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
sysroot=/var/tmp/aura-kali-rootfs
source="$sysroot/var/tmp/aura-iio-sensor-proxy-3.9"
mkdir -p "$source" "$project/build/kali/sensor-proxy"
cp -a "$project/sources/iio-sensor-proxy/iio-sensor-proxy-3.9/." "$source/"
chroot "$sysroot" meson setup /var/tmp/aura-iio-sensor-proxy-build /var/tmp/aura-iio-sensor-proxy-3.9 --prefix=/usr --libexecdir=libexec -Dssc-support=enabled -Dtests=false -Dgtk-tests=false -Dgtk_doc=false -Dudevrulesdir=/usr/lib/udev/rules.d -Dsystemdsystemunitdir=/usr/lib/systemd/system
chroot "$sysroot" meson compile -C /var/tmp/aura-iio-sensor-proxy-build -j 4
chroot "$sysroot" meson test -C /var/tmp/aura-iio-sensor-proxy-build --print-errorlogs
cp "$sysroot/var/tmp/aura-iio-sensor-proxy-build/src/iio-sensor-proxy" "$project/build/kali/sensor-proxy/"
aarch64-linux-gnu-strip --strip-debug "$project/build/kali/sensor-proxy/iio-sensor-proxy"
sha256sum "$project/build/kali/sensor-proxy/iio-sensor-proxy"
