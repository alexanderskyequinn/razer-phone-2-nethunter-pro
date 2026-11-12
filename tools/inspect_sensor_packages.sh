#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
cache=/var/tmp/aura-kali-rootfs/var/cache/apt/archives
out="$project/build/kali/sensor-packages"
mkdir -p "$out/extracted"
for package in hexagonrpcd libhexagonrpc0.4 libssc-bin; do
    cp "$cache/${package}"_*.deb "$out/"
    dpkg-deb -f "$out/${package}"_*.deb Package Version Depends
    dpkg-deb -x "$out/${package}"_*.deb "$out/extracted"
done
find "$out/extracted" -type f | head -65
cat "$out/extracted"/usr/lib/systemd/system/*
