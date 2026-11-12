#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
install -m 644 "$project/port/aura-imsa-pdp-probe.c" "$root/var/tmp/aura-imsa-pdp-probe.c"
chroot "$root" sh -c 'cc -O2 -Wall -Wextra -Werror /var/tmp/aura-imsa-pdp-probe.c -o /var/tmp/aura-imsa-pdp-probe $(pkg-config --cflags --libs qmi-glib qrtr-glib)'
install -m 755 "$root/var/tmp/aura-imsa-pdp-probe" "$project/build/kali/cellular/aura-imsa-pdp-probe"
sha256sum "$project/build/kali/cellular/aura-imsa-pdp-probe"
