#!/bin/bash
# Run in a private mount namespace as root. Every completed stage is retained.
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
state=/var/tmp/aura-kali-build/resume-state
mkdir -p "$root" "$state"
test "$(realpath "$root")" = /var/tmp/aura-kali-rootfs
export DEBIAN_FRONTEND=noninteractive
if [ ! -f "$state/foreign.done" ]; then
    debootstrap --foreign --arch=arm64 --variant=minbase \
      --components=main,contrib,non-free,non-free-firmware \
      --keyring="$project_dir/sources/kali-nethunter-pro/kali-archive-keyring.gpg" \
      kali-rolling "$root" https://kali.download/kali
    touch "$state/foreign.done"
fi
mkdir -p "$root/proc" "$root/sys" "$root/dev" "$root/run"
mount -t proc proc "$root/proc"
mount -t sysfs -o ro sysfs "$root/sys"
mount -t tmpfs -o mode=0755 tmpfs "$root/dev"
for spec in 'null 1 3 666' 'zero 1 5 666' 'random 1 8 666' 'urandom 1 9 666' 'tty 5 0 666'; do
    read -r name major minor mode <<<"$spec"
    mknod -m "$mode" "$root/dev/$name" c "$major" "$minor"
done
mkdir -p "$root/dev/pts" "$root/dev/shm"
mount -t devpts -o newinstance,ptmxmode=0666 devpts "$root/dev/pts"
ln -s pts/ptmx "$root/dev/ptmx"
ln -s /proc/self/fd "$root/dev/fd"
mount -t tmpfs tmpfs "$root/run"
if [ ! -f "$state/base-bootstrap.done" ]; then
    chroot "$root" /debootstrap/debootstrap --second-stage
    touch "$state/base-bootstrap.done"
fi
# debootstrap may unmount proc during its own cleanup.
mountpoint -q "$root/proc" || mount -t proc proc "$root/proc"
mountpoint -q "$root/sys" || mount -t sysfs -o ro sysfs "$root/sys"
cp --remove-destination -L /etc/resolv.conf "$root/etc/resolv.conf"
printf '#!/bin/sh\nexit 101\n' >"$root/usr/sbin/policy-rc.d"
chmod 755 "$root/usr/sbin/policy-rc.d"
install -m 0644 "$project_dir/sources/kali-nethunter-pro/kali-archive-keyring.gpg" "$root/usr/share/keyrings/kali-archive-keyring.gpg"
printf 'deb [signed-by=/usr/share/keyrings/kali-archive-keyring.gpg] https://kali.download/kali kali-rolling main contrib non-free non-free-firmware\n' >"$root/etc/apt/sources.list"
if [ ! -f "$state/repos.done" ]; then
    chroot "$root" apt-get update
    chroot "$root" apt-get install -y --no-install-recommends ca-certificates kali-archive-keyring mobian-archive-keyring
    sed 's/\r$//' "$project_dir/sources/kali-nethunter-pro/scripts/setup-apt.sh" >"$root/tmp/aura-setup-apt.sh"
    chroot "$root" sh /tmp/aura-setup-apt.sh kali-rolling forky
    chroot "$root" apt-get update
    touch "$state/repos.done"
fi
if [ ! -f "$state/base.done" ]; then
    chroot "$root" apt-get install -y --no-install-recommends \
      mobian-base kali-linux-core kali-themes-mobile openssh-server vim \
      curl systemd-repart dbus-user-session libpam-systemd
    touch "$state/base.done"
fi
# Produce a dependency report before choosing replacements for the broken
# mobian-phosh -> phosh-full metapackage in the current official recipe.
chroot "$root" apt-cache policy phosh phoc phosh-core phosh-full phosh-session \
  mobian-phosh mobian-phosh-base greetd phog squeekboard >"$state/desktop-policy.txt"
chroot "$root" apt-cache depends mobian-phosh-base phosh phosh-core >"$state/desktop-dependencies.txt"
echo 'Persistent Kali base ready; desktop dependency reports saved.'
