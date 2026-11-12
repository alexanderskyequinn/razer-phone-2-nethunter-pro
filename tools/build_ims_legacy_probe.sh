#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
install -m 644 "$project/port/aura-ims-legacy-probe.c" "$root/var/tmp/aura-ims-legacy-probe.c"
chroot "$root" sh -c 'cc -O2 -Wall -Wextra -Werror /var/tmp/aura-ims-legacy-probe.c -o /var/tmp/aura-ims-legacy-probe $(pkg-config --cflags --libs qmi-glib qrtr-glib)'
install -m 755 "$root/var/tmp/aura-ims-legacy-probe" "$project/build/kali/cellular/aura-ims-legacy-probe"
sha256sum "$project/build/kali/cellular/aura-ims-legacy-probe"
