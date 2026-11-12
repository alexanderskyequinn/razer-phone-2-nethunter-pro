#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
test -f /var/tmp/aura-kali-rootfs/etc/aura-install-id
tar -xf "$project/build/kali/logo-app/logo-app.tar" -C /var/tmp/aura-kali-rootfs
bash "$project/tools/stage_logo_control_root.sh"
chroot /var/tmp/aura-kali-rootfs desktop-file-validate /usr/share/applications/org.aura.LogoLight.desktop
