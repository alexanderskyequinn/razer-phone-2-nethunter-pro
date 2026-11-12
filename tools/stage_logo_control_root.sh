#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
test -f /var/tmp/aura-kali-rootfs/etc/aura-install-id
install -m 755 "$project/port/kali-overlay/usr/local/sbin/aura-logo" /var/tmp/aura-kali-rootfs/usr/local/sbin/aura-logo
install -m 644 "$project/port/kali-overlay/etc/systemd/system/aura-logo.service" /var/tmp/aura-kali-rootfs/etc/systemd/system/aura-logo.service
link=/var/tmp/aura-kali-rootfs/usr/sbin/aura-logo
if [ -e "$link" ] || [ -L "$link" ]; then
    test "$(readlink "$link")" = /usr/local/sbin/aura-logo
else
    ln -s /usr/local/sbin/aura-logo "$link"
fi
sha256sum /var/tmp/aura-kali-rootfs/usr/local/sbin/aura-logo
