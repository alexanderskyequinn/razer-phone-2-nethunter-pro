#!/bin/bash
# Run as root in a private mount namespace after build_kali_resumable.sh.
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
state=/var/tmp/aura-kali-build/resume-state
test -f "$state/base.done"
export DEBIAN_FRONTEND=noninteractive
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
cp --remove-destination -L /etc/resolv.conf "$root/etc/resolv.conf"
if [ ! -f "$state/desktop.done" ]; then
    # mobian-phosh currently depends on absent phosh-full/phosh-core packages.
    # Install the real Kali packages; retain a manifest of this deliberate fork.
    chroot "$root" apt-get install -y --no-install-recommends \
      phosh phoc squeekboard phosh-osk-stevia gnome-session-bin gnome-session-common \
      gnome-settings-daemon phosh-mobile-tweaks phosh-plugins feedbackd \
      iio-sensor-proxy gnome-keyring gnome-control-center gnome-console \
      xdg-desktop-portal-gtk xdg-desktop-portal-wlr xdg-user-dirs \
      fonts-noto-core fonts-noto-color-emoji firefox-esr powersupply-gtk loupe \
      gnome-sound-recorder webext-ublock-origin-firefox libcap2-bin \
      libpam-gnome-keyring dconf-cli grim libdrm-tests evtest modemmanager libqmi-utils \
      81voltd gnome-calls chatty
    touch "$state/desktop.done"
fi
# Also cover resumes of images prepared before Stevia was selected.
if ! chroot "$root" dpkg-query -W -f='${Status}' phosh-osk-stevia 2>/dev/null | grep -q 'install ok installed'; then
    chroot "$root" apt-get install -y --no-install-recommends phosh-osk-stevia
fi
for package in modemmanager libqmi-utils 81voltd gnome-calls chatty pkexec python3-gi gir1.2-gtk-3.0 nautilus wlopm gnome-snapshot libspa-0.2-libcamera gstreamer1.0-libcamera gstreamer1.0-pipewire gstreamer1.0-gl gstreamer1.0-gtk4; do
    if ! chroot "$root" dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
        chroot "$root" apt-get install -y --no-install-recommends "$package"
    fi
done
if [ ! -f "$state/fossfrog.done" ]; then
    ff=https://raw.githubusercontent.com/Shubhamvis98/deb/26537e88a5b003bd56b095a74c8b98ddc5e6b8cc
    curl -fsSL -o "$root/etc/apt/trusted.gpg.d/fossfrog.gpg" "$ff/fossfrog.gpg"
    curl -fsSL -o "$root/etc/apt/sources.list.d/fossfrog.list" "$ff/fossfrog.list"
    printf '%s\n' 'Package: *' 'Pin: release o=fossfrog' 'Pin-Priority: 100' >"$root/etc/apt/preferences.d/10-fossfrog-priority"
    chroot "$root" apt-get update
    touch "$state/fossfrog.done"
fi
if [ ! -f "$state/nethunter.done" ]; then
    chroot "$root" apt-get install -y --no-install-recommends nethunter hijacker kalitorify
    touch "$state/nethunter.done"
fi
# Apply the selected stock app suite on fresh builds and resumed build roots.
mapfile -t aura_apps < <(python3 - "$project_dir/port/app-packages.json" <<'PY'
import json,sys
data=json.load(open(sys.argv[1]))
print('\n'.join(data['everyday']+data['kali']+data['media_support']))
PY
)
chroot "$root" apt-get install -y --no-remove "${aura_apps[@]}"
chroot "$root" systemctl disable smartmontools.service
chroot "$root" dpkg-query -W >"$state/packages.txt"
chroot "$root" dpkg --audit
echo 'Kali native desktop and NetHunter packages installed.'
