#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
root=/var/tmp/aura-kali-rootfs
source=/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa
output=/var/tmp/aura-libcamera-build
test "$(sha256sum "$project/sources/libcamera_0.7.2.orig.tar.gz" | cut -d ' ' -f1)" = e27f5670fe9443eebc8e2f24235cd20b533324ef481a3684d34c78f1c3a12afb
python3 "$project/tools/patch_libcamera_aura.py"
python3 "$project/tools/patch_camera_preview.py"
python3 "$project/tools/patch_camera_awb.py"
python3 "$project/tools/patch_camera_photo.py"
python3 "$project/tools/patch_camera_autofocus.py"
python3 "$project/tools/patch_libcamera_telecamera.py"
python3 "$project/tools/patch_telefocus_autofocus.py"
python3 "$project/tools/patch_camera_focus_retry.py"
python3 "$project/tools/patch_camera_focus_timing.py"
chroot "$root" meson setup "$output" "$source" --prefix=/opt/aura-camera --libdir=lib --buildtype=release -Dpipelines=simple -Dipas=simple -Dcam=enabled -Dcam-jpeg=enabled -Dcam-output-sdl2=enabled -Dcam-output-kms=disabled -Dqcam=disabled -Dgstreamer=disabled -Dpycamera=disabled -Ddocumentation=disabled -Dtest=false -Dtracing=disabled -Dlc-compliance=disabled -Dv4l2=disabled -Dlibdw=disabled -Dlibunwind=disabled -Dsoftisp-gpu=enabled
chroot "$root" meson compile -C "$output" -j 16
chroot "$root" meson install -C "$output" --destdir /var/tmp/aura-libcamera-stage
tar -C "$root/var/tmp/aura-libcamera-stage" -czf "$project/build/kali/camera/aura-libcamera.tar.gz" opt
sha256sum "$project/build/kali/camera/aura-libcamera.tar.gz"
