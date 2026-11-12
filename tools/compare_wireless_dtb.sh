#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
out="$project/build/kali"
dtc -q -I dtb -O dts "$out/v14-wireless-baseline/board.dtb" -o "$out/wireless-old-board.dts"
dtc -q -I dtb -O dts "$out/wireless-probe-kernel/sdm845-razer-aura.dtb" -o "$out/wireless-new-board.dts"
diff -u "$out/wireless-old-board.dts" "$out/wireless-new-board.dts" || test "$?" = 1
