#!/bin/bash
set -euo pipefail
chroot /var/tmp/aura-kali-rootfs env PHOC_AURA_LIVE_ROTATION=1 xvfb-run -a meson test -C /var/tmp/aura-phoc-build --no-rebuild outputs-states layer-shell timed-animation --print-errorlogs --timeout-multiplier 3
