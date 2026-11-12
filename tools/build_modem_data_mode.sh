#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
install -m 644 "$project/port/aura-modem-data-mode.c" "$root/var/tmp/aura-modem-data-mode.c"
chroot "$root" sh -c 'cc -O2 -Wall -Wextra -Werror /var/tmp/aura-modem-data-mode.c -o /var/tmp/aura-modem-data-mode $(pkg-config --cflags --libs qmi-glib qrtr-glib)'
mkdir -p "$project/build/kali/cellular"
install -m 755 "$root/var/tmp/aura-modem-data-mode" "$project/build/kali/cellular/aura-modem-data-mode"
sha256sum "$project/build/kali/cellular/aura-modem-data-mode"
