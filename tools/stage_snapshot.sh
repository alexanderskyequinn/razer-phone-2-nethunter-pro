#!/bin/bash
set -euo pipefail
root=/var/tmp/aura-kali-rootfs
project=$(cd "$(dirname "$0")/.." && pwd)
mount --make-rprivate /
mount -t proc proc "$root/proc"
mount -t sysfs -o ro sysfs "$root/sys"
export DEBIAN_FRONTEND=noninteractive
chroot "$root" apt-get install -y --no-install-recommends gnome-snapshot libspa-0.2-libcamera gstreamer1.0-libcamera gstreamer1.0-pipewire gstreamer1.0-gl gstreamer1.0-gtk4
bash "$project/tools/stage_camera_userspace.sh"
chroot "$root" dpkg --audit
