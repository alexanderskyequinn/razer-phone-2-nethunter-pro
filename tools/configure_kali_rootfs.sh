#!/bin/bash
set -euo pipefail
tools_dir=$(cd "$(dirname "$0")" && pwd)
root=/var/tmp/aura-kali-rootfs
mount -t proc proc "$root/proc"
mount -t sysfs -o ro sysfs "$root/sys"
mount -t tmpfs -o mode=0755 tmpfs "$root/dev"
for spec in 'null 1 3 666' 'zero 1 5 666' 'random 1 8 666' 'urandom 1 9 666' 'tty 5 0 666'; do
    read -r name major minor mode <<<"$spec"
    mknod -m "$mode" "$root/dev/$name" c "$major" "$minor"
done
mount -t tmpfs tmpfs "$root/run"
python3 "$tools_dir/configure_kali_rootfs.py"
mkdir -p "$root/run/sshd"
chroot "$root" /usr/sbin/sshd -t
chroot "$root" /usr/sbin/sshd -T >"$tools_dir/../build/kali/sshd-effective.txt"
chroot "$root" systemd-analyze verify aura-usb-gadget.service aura-usb-dhcp.service aura-first-boot-guard.service phosh.service ssh.service >"$tools_dir/../build/kali/service-validation.txt" 2>&1
