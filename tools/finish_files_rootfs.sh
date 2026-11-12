#!/bin/bash
set -euo pipefail
root=/var/tmp/aura-kali-rootfs
mount --make-rprivate /
mount -t proc proc "$root/proc"
mount -t sysfs -o ro sysfs "$root/sys"
export DEBIAN_FRONTEND=noninteractive
chroot "$root" dpkg --configure -a
chroot "$root" dpkg --audit
