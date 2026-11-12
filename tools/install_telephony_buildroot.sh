#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
test -f "$root/etc/aura-install-id"
cd "$project/build/kali/telephony-packages"
sha256sum --status -c SHA256SUMS
install -d "$root/var/tmp/aura-telephony-debs"
cp ./*.deb "$root/var/tmp/aura-telephony-debs/"
chroot "$root" sh -c 'cd /var/tmp/aura-telephony-debs && DEBIAN_FRONTEND=noninteractive dpkg -i ./*.deb'
chroot "$root" dpkg --audit
systemctl --root="$root" enable 81voltd
