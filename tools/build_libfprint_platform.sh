#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
python3 "$project/tools/prepare_libfprint_platform.py"
work=/var/tmp/aura-libfprint-platform
meson setup "$work/host" "$work/source" --prefix=/opt/aura-fprint -Ddrivers=aura_fpc -Dintrospection=false -Ddoc=false -Dinstalled-tests=false -Dudev_rules=disabled -Dudev_hwdb=disabled
ninja -C "$work/host"
gcc -Wall -Wextra -Werror "$project/tests/fprint-platform-enumerate.c" -I"$work/source" -I"$work/host/libfprint" $(pkg-config --cflags --libs glib-2.0 gio-2.0) -L"$work/host/libfprint" -Wl,-rpath,"$work/host/libfprint" -lfprint-2 -o "$work/enumerate"
"$work/enumerate"
