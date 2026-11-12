#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
build_dir=$(cat "$project_dir/build/diagnostic/linux-build-directory.txt")
"$build_dir/musl/bin/musl-gcc" -static -Os -std=gnu17 -o "$project_dir/build/diagnostic/return-to-bootloader" "$project_dir/diagnostic/return_to_bootloader.c"
aarch64-linux-gnu-readelf -h "$project_dir/build/diagnostic/return-to-bootloader"
if aarch64-linux-gnu-readelf -l "$project_dir/build/diagnostic/return-to-bootloader" | grep -q INTERP; then exit 1; fi
sh -n "$project_dir/diagnostic/init"
