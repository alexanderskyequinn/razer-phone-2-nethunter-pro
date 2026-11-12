Aura RAM Recovery (development)

This is a separate, device-specific recovery for the Razer Phone 2 native
Kali port. Slot B contains Kali; slot A contains this RAM-only recovery.
There is no separate recovery partition on this A/B device.

The image uses the verified v26 kernel and device tree. It does not mount
Android system/vendor/oem, Kali userdata, or the microSD card at startup.
Essential Qualcomm bootloader, signed firmware and calibration partitions
must remain in place. A standalone Linux userspace does not replace them.

Build in WSL as root:
  python3 tools/build_aura_rescue.py --test-seconds 0

The default build is local-only: no operator key, SSH daemon, USB network or
HTTP listener. The builder validates shell syntax, ARM64 dependencies and the
packed boot image. It never includes private keys or fingerprint databases.
For an explicitly personalized development image, pass --authorized-key PATH.
Only that opt-in build has the remote interfaces described below. Each remote
RAM boot generates a fresh host key; use a unique --session identifier with
tools/kali_rescue_ssh.py, which pins that key for the session.

Current development interface:
  Volume buttons select Start Kali, Download Mode or Power Off.
  Power activates the selected action.
  Opt-in development USB SSH: root@192.0.2.1, public-key authentication only.
  Opt-in USB status: http://192.0.2.1/status.txt (read-only diagnostic log).
  No Wi-Fi listener or password login is configured.

After connecting:
  aura-rescue status
  aura-rescue check              offline, read-only ext4 check
  aura-rescue mount-readonly     mounts Kali with ro,noload
  aura-rescue unmount
  aura-rescue repair --confirm   changes filesystem metadata; use deliberately
  aura-rescue boot-kali
  aura-rescue bootloader
  aura-rescue poweroff

The normal image has no automatic reboot timer. A development build may use
--test-seconds 180 to return to Kali after three minutes.
The original slot-A boot/dtbo backup is stored on Kali under
/var/lib/aura/recovery-rollbacks. Slot B is not overwritten by the installer.
This backup is not accessible while userdata remains unmounted.

Do not describe an image as tested based only on the build succeeding.
Hardware acceptance requires a readable screen, no automatic filesystem mounts,
physical buttons and return to Kali. Development images also require their
authenticated SSH and offline filesystem-check paths to be tested.
Read build/kali/native-storage-progress.json for the actual test status.

Observed initial defects and corrections:
  OpenSSH daemon startup requires an absolute executable path.
  Minimal mdev does not create the partition-label links qbootctl needs.
  Native framebuffer text is tiny; screen.c draws a large recovery menu
  directly through bounded writes to the registered 1440x2560 framebuffer.
  Upstream qbootctl assigned the active type GUID to A even when selecting B.
  The corrected static selector assigns GUIDs according to the requested slot
  and grants seven boot retries. Do not replace it with upstream qbootctl for
  slot switching. tools/test_recovery_slot_fix.py tests the actual C switching
  function with mocked I/O against saved GPT metadata in both directions.

The Recovery desktop shortcut authenticates locally, checks installed image
and selector hashes, and selects A. START KALI selects B. The corrected timed
image completed a round trip with partition GUIDs and boundaries unchanged.
See build/kali/native-storage-progress.json for the final image test status.

The currently installed recovery is still the previously tested personalized
development image. The new local-only release recovery has been built but has
not yet passed its own hardware acceptance. Shipping also requires a tested
installation workflow. Never publish device-data, installed biometrics, PIN
handles, modem NV/calibration data, or a clone of the user's live filesystem.
