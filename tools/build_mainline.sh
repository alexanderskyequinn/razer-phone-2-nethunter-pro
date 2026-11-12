#!/bin/bash
set -euo pipefail
project_dir=$(cd "$(dirname "$0")/.." && pwd)
source_dir=$(cat "$project_dir/build/mainline/source-directory.txt")
test "$source_dir" = /var/tmp/aura-mainline-6.18.2/linux
test "$(git -C "$source_dir" rev-parse HEAD)" = a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0
output_dir=/var/tmp/aura-mainline-6.18.2/out
mkdir -p "$output_dir"
cp "$project_dir/port/"sdm845-razer-aura*.dts* "$source_dir/arch/arm64/boot/dts/qcom/"
python3 "$project_dir/tools/install_panel_driver.py" "$source_dir"
python3 "$project_dir/tools/install_charger_fixes.py" "$source_dir"
python3 "$project_dir/tools/install_haptics_limit.py" "$source_dir"
python3 "$project_dir/tools/install_radio_audio_fixes.py" "$source_dir"
python3 "$project_dir/tools/patch_modem_nv.py"
python3 "$project_dir/tools/patch_wifi_startup.py"
python3 "$project_dir/tools/patch_display_irq_lifetime.py"
python3 "$project_dir/tools/patch_logo_supply.py"
cp "$project_dir/port/aura-bringup.config" "$output_dir/aura-bringup.config"
export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
cd "$source_dir"
make O="$output_dir" defconfig
scripts/kconfig/merge_config.sh -m -O "$output_dir" "$output_dir/.config" arch/arm64/configs/sdm845.config "$output_dir/aura-bringup.config"
make O="$output_dir" olddefconfig
make O="$output_dir" -j8 Image.gz qcom/sdm845-razer-aura.dtb
cp "$output_dir/arch/arm64/boot/Image.gz" "$project_dir/build/mainline/"
cp "$output_dir/arch/arm64/boot/dts/qcom/sdm845-razer-aura.dtb" "$project_dir/build/mainline/"
cp "$output_dir/.config" "$project_dir/build/mainline/kernel.config"
sha256sum "$project_dir/build/mainline/Image.gz" "$project_dir/build/mainline/sdm845-razer-aura.dtb"
bash "$project_dir/tools/build_torch_module.sh"
python3 "$project_dir/tools/prepare_camera_module.py"
bash "$project_dir/tools/build_camera_module.sh"
bash "$project_dir/tools/build_focus_module.sh"
