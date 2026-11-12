#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
test -f "$root/etc/aura-install-id"
DEBIAN_FRONTEND=noninteractive chroot "$root" apt-get -o Acquire::Retries=1 -o Acquire::https::Timeout=20 install -y --no-install-recommends pkexec
mkdir -p "$project/build/kali/logo-app"
chroot "$root" apt-get -o Acquire::Retries=1 -o Acquire::https::Timeout=20 --download-only --reinstall install -y pkexec
cp "$root"/var/cache/apt/archives/pkexec_*_arm64.deb "$project/build/kali/logo-app/"
sha256sum "$project/build/kali/logo-app/"*.deb
