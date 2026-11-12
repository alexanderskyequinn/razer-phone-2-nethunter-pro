# Razer Phone 2 — native Kali / NetHunter Pro port

Experimental native Linux support for the **Razer Phone 2 (aura, SDM845)**,
running Kali rolling, Phosh and NetHunter userspace. This runs on the phone's
hardware; it is not an Android chroot.

**Development source snapshot, not a ready-to-flash release.** This project is
unofficial and is not an officially supported Kali NetHunter Pro device image.
Hardware results below were recorded on one development phone through
**10 October 2026**. Publishing the source does not constitute a fresh hardware
qualification or a reproducible clean-install test.

## Current state

- Native boot, persistent storage, display, touch and Adreno 630 acceleration work.
- Wi-Fi connects; throughput needs work. Bluetooth pairing works; profiles and
  sleep recovery need further testing.
- Both rear cameras provide preview, autofocus and upright photos. Video with
  audio was verified; stabilization, still-flash synchronization and image quality
  remain incomplete.
- Speakers, microphone, rotation, keyboard, haptics, flashlight, logo lighting,
  microSD and Qi charging have working basic functions.
- Fingerprint enrollment works through a candidate libfprint/fprintd integration
  in standard GNOME Settings. **Verification is still unreliable: the latest
  fresh enrollment returned no match. Fingerprint unlock is not enabled.**
- LTE browsing was verified earlier. Calls/SMS and remaining SIM work are deferred.
- Front-camera failure predates Linux on the test device. NFC tag detection,
  GNSS, ambient light/proximity and longer power-management testing remain open.

See [the hardware matrix](docs/HARDWARE.md) for qualifications and remaining work.

## Repository layout

| Path | Contents |
| --- | --- |
| `port/` | Board device trees, drivers, kernel/userspace patches, service templates and experimental apps |
| `tools/` | Development build, packaging, inspection and historical test helpers |
| `tests/` | Synthetic protocol, storage, process, UI and driver tests |
| `docs/` | Build context, dependencies, publication scope and hardware status |

Start with [development notes](docs/DEVELOPMENT.md) and
[source/licensing notes](COPYING.md). Older component notes describe intermediate
experiments; this README and the hardware matrix take precedence for current status.

## Installation status

There is **no supported end-to-end installation procedure or binary release in
this repository yet**. Scripts refer to omitted local firmware, source checkouts,
package caches, build manifests and earlier test artifacts. They are development
recipes, not a one-command installer. Several historical helpers can flash or
rewrite partitions; review them before use. Simply replacing placeholders does
not make a recipe suitable for another device.

The development installation uses native ext4 storage on `userdata` and retains
required boot-chain, firmware and calibration partitions. Deleting all Android-era
partitions is not a supported migration path. Use only a Razer Phone 2 with an
unlocked bootloader and your own recovery/backups when developing this port.

Clean installation, stock onboarding, persistent stock fingerprint integration,
and portable recovery still need completion and independent device testing.

## What is deliberately absent

No phone backups, calibration/NV data, proprietary firmware or vendor libraries,
root filesystem images, camera captures, fingerprint templates, PIN records,
SSH keys, Wi-Fi profiles, or raw device logs are included. Device-specific guards
in the public copy use placeholders; development network examples use reserved
documentation addresses. See [publication scope](docs/PUBLICATION.md).

## Contributing

Useful targets include reliable fingerprint matching, clean-install tooling,
Wi-Fi throughput, suspend/power qualification, and remaining camera/peripheral
support. Include the kernel/userspace revision and reproduction steps in reports.
Sanitize device logs and do not attach credentials, biometric data, calibration
partitions or vendor firmware. Preserve existing file-level license notices.
