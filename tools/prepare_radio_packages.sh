#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
mkdir -p /var/tmp/aura-kali-build/radio-debs/partial /var/tmp/aura-kali-build/radio-inspect
chroot "$root" apt-get -y --download-only --no-install-recommends install rmtfs protection-domain-mapper qrtr-tools tqftpserv iw
for package in "$root"/var/cache/apt/archives/{rmtfs,protection-domain-mapper,qrtr-tools,tqftpserv,libqrtr1,libqmi-glib5,iw}_*.deb; do
    [ ! -f "$package" ] || cp "$package" /var/tmp/aura-kali-build/radio-debs/
done
for package in /var/tmp/aura-kali-build/radio-debs/*.deb; do
    dpkg-deb -x "$package" /var/tmp/aura-kali-build/radio-inspect
done
cd /var/tmp/aura-kali-build/radio-debs
tar -cf "$project_dir/build/kali/radio-debs.tar" ./*.deb
find /var/tmp/aura-kali-build/radio-inspect -name '*.service' -print -exec cat {} \;
