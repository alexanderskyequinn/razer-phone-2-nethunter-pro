#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
mkdir -p "$root/var/tmp/aura-libcamera-work"
archive="$project/sources/libcamera_0.7.2.orig.tar.gz"
if [ ! -f "$archive" ]; then
    curl -fL --max-time 60 https://kali.download/kali/pool/main/libc/libcamera/libcamera_0.7.2.orig.tar.gz -o "$archive"
fi
echo "e27f5670fe9443eebc8e2f24235cd20b533324ef481a3684d34c78f1c3a12afb  $archive" | sha256sum -c -
if [ ! -d "$root/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa" ]; then
    tar -xzf "$archive" -C "$root/var/tmp/aura-libcamera-work"
fi
chroot "$root" apt-get install -y --no-install-recommends libyaml-dev libevent-dev libsdl2-dev libjpeg-dev libgnutls28-dev libssl-dev python3-ply python3-jinja2 python3-yaml libdrm-dev libegl-dev libgles-dev
