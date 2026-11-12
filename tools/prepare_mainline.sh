#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
work_dir=/var/tmp/aura-mainline-6.18.2
source_dir=$work_dir/linux
revision=a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0
mkdir -p "$project_dir/build/mainline" "$work_dir"
if [ ! -d "$source_dir" ]; then
    git clone --depth 1 --branch sdm845-6.18.2-r0 https://gitlab.com/sdm845-mainline/linux.git "$source_dir" >"$project_dir/build/mainline/source-download.log" 2>&1
fi
test "$(git -C "$source_dir" rev-parse HEAD)" = "$revision"
printf '%s\n' "$source_dir" >"$project_dir/build/mainline/source-directory.txt"
git -C "$source_dir" show -s --format=fuller HEAD
head -n 7 "$source_dir/Makefile"
printf '\nMemory and available build storage:\n'
free -h
df -h "$work_dir"
