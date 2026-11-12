#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
test -f "$root/etc/aura-install-id"
policy="$root/usr/sbin/policy-rc.d"
backup=$(mktemp)
had_policy=0
if test -e "$policy"; then cp -a "$policy" "$backup"; had_policy=1; fi
restore_policy() {
    if test "$had_policy" = 1; then cp -a "$backup" "$policy"; else rm -f "$policy"; fi
    rm -f "$backup"
}
trap restore_policy EXIT
printf '#!/bin/sh\nexit 101\n' > "$policy"
chmod 755 "$policy"
mkdir -p "$root/var/tmp/aura-modem-debs"
cp "$project/build/kali/modem-packages/modemmanager_1.24.2-2+b1_arm64.deb" "$project/build/kali/modem-packages/libqmi-utils_1.38.0-1+b1_arm64.deb" "$root/var/tmp/aura-modem-debs/"
chroot "$root" sh -c 'DEBIAN_FRONTEND=noninteractive dpkg -i /var/tmp/aura-modem-debs/*.deb'
chroot "$root" dpkg --audit
test -f "$root/usr/lib/systemd/system/ModemManager.service"
