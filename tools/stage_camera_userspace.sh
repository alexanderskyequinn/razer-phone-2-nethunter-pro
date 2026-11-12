#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
archive="$project/build/kali/camera/aura-libcamera.tar.gz"
expected=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["archive_sha256"])' "$project/build/kali/camera/userspace-manifest.json")
test "$(sha256sum "$archive" | cut -d ' ' -f1)" = "$expected"
test -f "$root/etc/os-release"
tar -xzf "$archive" -C "$root" opt/aura-camera
install -m 0755 "$project/port/kali-overlay/usr/local/bin/aura-camera-preview" "$root/usr/local/bin/aura-camera-preview"
install -m 0644 "$project/port/kali-overlay/usr/share/applications/aura-camera-preview.desktop" "$root/usr/share/applications/aura-camera-preview.desktop"
install -m 0755 "$project/port/kali-overlay/usr/local/bin/aura-camera" "$root/usr/local/bin/aura-camera"
install -m 0644 "$project/port/kali-overlay/usr/share/applications/aura-camera.desktop" "$root/usr/share/applications/aura-camera.desktop"
test -x "$root/opt/aura-camera/bin/cam"
for service in pipewire wireplumber; do
    install -D -m 0644 "$project/port/kali-overlay/etc/systemd/user/$service.service.d/60-aura-camera.conf" "$root/etc/systemd/user/$service.service.d/60-aura-camera.conf"
done
printf 'Private camera userspace and desktop launcher staged for future rootfs builds.\n'
