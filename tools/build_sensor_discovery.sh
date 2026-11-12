#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
install -m 644 "$project/port/aura-sensor-discovery.c" "$root/var/tmp/aura-sensor-discovery.c"
chroot "$root" sh -c 'cc -O2 -Wall -Wextra -Werror /var/tmp/aura-sensor-discovery.c -o /var/tmp/aura-sensor-discovery $(pkg-config --cflags --libs qmi-glib qrtr-glib)'
mkdir -p "$project/build/kali/sensors"
install -m 755 "$root/var/tmp/aura-sensor-discovery" "$project/build/kali/sensors/aura-sensor-discovery"
sha256sum "$project/build/kali/sensors/aura-sensor-discovery"
