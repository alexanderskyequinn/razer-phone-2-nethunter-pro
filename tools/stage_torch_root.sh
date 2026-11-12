#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
test "$(cat "$root/etc/aura-install-id")" = 'REPLACE_WITH_YOUR_INSTALL_ID'
destination="$root/usr/lib/modules/6.18.2-aura-bringup1+/updates/aura"
install -d "$destination"
install -m 644 "$project/build/kali/torch/leds-aura-lm3644.ko" "$destination/"
depmod -b "$root" 6.18.2-aura-bringup1+
sha256sum "$destination/leds-aura-lm3644.ko"
