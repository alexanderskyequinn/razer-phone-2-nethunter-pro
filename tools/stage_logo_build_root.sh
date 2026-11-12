#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
dest=/var/tmp/aura-kali-rootfs/usr/lib/modules/6.18.2-aura-bringup1+/updates/aura
test -f /var/tmp/aura-kali-rootfs/etc/aura-install-id
mkdir -p "$dest"
install -m 644 "$project/build/kali/logo-modules/leds-lp55xx-common.ko" "$project/build/kali/logo-modules/leds-lp5523.ko" "$dest/"
depmod -b /var/tmp/aura-kali-rootfs 6.18.2-aura-bringup1+
sha256sum "$dest/leds-lp55xx-common.ko" "$dest/leds-lp5523.ko"
