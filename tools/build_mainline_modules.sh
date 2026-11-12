#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
source_dir=/var/tmp/aura-mainline-6.18.2/linux
output_dir=/var/tmp/aura-mainline-6.18.2/out
install_dir=/var/tmp/aura-mainline-6.18.2/module-install
test "$(git -C "$source_dir" rev-parse HEAD)" = a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
make -C "$source_dir" O="$output_dir" -j8 modules
make -C "$source_dir" O="$output_dir" INSTALL_MOD_PATH="$install_dir" INSTALL_MOD_STRIP=1 modules_install
make -s -C "$source_dir" O="$output_dir" kernelrelease >"$project_dir/build/mainline/kernel-release.txt"
printf '%s\n' "$install_dir" >"$project_dir/build/mainline/modules-directory.txt"
