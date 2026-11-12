#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
install -m 644 "$project/port/aura-ims-enable.c" "$root/var/tmp/aura-ims-enable.c"
chroot "$root" sh -c 'cc -O2 -Wall -Wextra -Werror /var/tmp/aura-ims-enable.c -o /var/tmp/aura-ims-enable $(pkg-config --cflags --libs qmi-glib qrtr-glib)'
install -m 755 "$root/var/tmp/aura-ims-enable" "$project/build/kali/cellular/aura-ims-enable"
sha256sum "$project/build/kali/cellular/aura-ims-enable"
