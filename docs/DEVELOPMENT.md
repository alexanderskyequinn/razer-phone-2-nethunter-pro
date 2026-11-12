# Development context

The original build environment was Ubuntu under WSL, with an AArch64 cross
compiler and QEMU user emulation for ARM64 Kali userspace. Most scripts derive
the project root from their own path, but working trees still use fixed
`/var/tmp/aura-*` directories. Some host/device helpers assume Windows OpenSSH
or Android platform tools. Host-specific paths need adaptation.

## Pinned source inputs

| Component | Upstream | Recorded revision |
| --- | --- | --- |
| Mainline SDM845 kernel | https://gitlab.com/sdm845-mainline/linux | `a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0` (`sdm845-6.18.2-r0`) |
| libfprint | https://gitlab.freedesktop.org/libfprint/libfprint | `6f9479c3d55f847c1b3769f28ceb99227f9858cf` |
| QSEE supplicant | https://github.com/wrobelda/qsee-supplicant | `36e06680cf7f690fccbdcd07abc2a64c4bb061d8` |
| Razer Android device reference | https://github.com/LineageOS/android_device_razer_aura | `bad0518b5a663c08a0765809e2c87a6870485287` |
| Razer Android kernel reference | https://github.com/LineageOS/android_kernel_razer_sdm845 | `3a6cba3be385c5368d316fca52ecd51cf734345f` |
| NetHunter Pro recipes | https://gitlab.com/kalilinux/nethunter/build-scripts/kali-nethunter-pro | `2347367d86f54f92e32005b428600a878bcf1c60` |

Full upstream checkouts are not vendored. For the fingerprint builds, place
libfprint and qsee-supplicant checkouts at `sources/libfprint-upstream` and
`sources/qsee-supplicant`, respectively, and check out the revisions above.
`tools/prepare_mainline.sh` obtains and verifies the kernel baseline.
`tools/prepare_libcamera_source.sh` records the libcamera 0.7.2 archive hash.
Other recipes contain their own source and package constraints.

The port evolves through additional module builds and userspace patches; running
`build_mainline.sh` alone does not reproduce the final development phone.
Kernel source, generated DTBs, module ABI, firmware inputs and userspace changes
must be kept consistent. A complete reproducible release pipeline is unfinished.

## Build entry points to inspect

- Kernel: `tools/prepare_mainline.sh`, `tools/build_mainline.sh` and the module
  build scripts. Typical dependencies include GCC/binutils for AArch64, make,
  bc, bison, flex, libelf/OpenSSL development headers and dtc.
- Camera: the libcamera preparation/build helpers and `port/libcamera-*.patch`.
- Fingerprint: `tools/build_fpc_bio.sh`, `tools/build_fprint_prompt.py`,
  `tools/build_libfprint_operations.py` and `tools/package_fprint_operations.py`.
- Recovery and release experiments: `tools/build_aura_rescue.py`,
  `tools/prepare_kali_release.py` and related audit/build helpers. These require
  local inputs not supplied here and have not passed a complete clean-device test.

Development configuration helpers no longer contain a shared test PIN. Where
required, supply your own numeric `AURA_TEST_PIN` explicitly. These helpers still
produce development configurations, including opt-in remote-access components;
they are not the proposed distribution's final onboarding flow. SSH key files,
known-host entries, install IDs and device serials must be supplied locally.
The source publication does not enable remote access on any device.

## Testing without the phone

Use a disposable Linux build environment for tests that require root: the
fingerprint Python tests create synthetic state beneath `/var/lib` and exercise
ownership and process isolation. They do not need real fingerprint records.

```sh
sudo python3 tests/test_fprint_store.py
sudo python3 tests/test_fprint_worker.py
sudo python3 tests/test_fprint_bridge.py
```

`tools/build_fpc_bio.sh` builds mock-based native protocol tests with ASan/UBSan,
then cross-compiles the ARM64 helper. Create `build/kali/fingerprint` first and
install `gcc-aarch64-linux-gnu`. `tools/test_libfprint_operations.py` requires its
prepared host libfprint build and umockdev. Passing synthetic tests is not proof
that live biometric matching, authentication or a fresh installation works.

`record_*` helpers summarize private historical evidence and generally cannot run
in this checkout. The omitted `diagnostic/` directory contains device-specific
orchestration; references to it and `test-runs/` are historical, not missing public
test fixtures. Do not use the original phone's old hashes as proof for a new build.
