Razer Phone 2 fingerprint bring-up (experimental)
================================================================

This directory contains electrical resource support and a secure fingerprint
backend for fpctzappfingerprint. A candidate libfprint/fprintd integration now
supports enrollment through standard GNOME Settings. The latest fresh record
reloads but fails same-finger verification. Fingerprint unlock is disabled.
Earlier engineering tests did match a finger; those results do not establish
reliable current authentication. See ../stock-integration-status.txt and the
root README. Historical bring-up sections below are retained for context.

Electrical resources
--------------------
aura_fpc_resources.c builds against 6.18.2-aura-bringup1+. The opt-in device
tree is ../sdm845-razer-aura-fingerprint.dtsi; its node remains disabled.
GPIO95 is active-low reset; GPIO121 is a rising-edge interrupt. Binding does
not reset the sensor. Root-only reset=1 performs the stock timing sequence.
irq and irq_count are readable and pollable sysfs attributes. No SPI access,
regulator changes, wakeup enablement, or secure calls are performed here.

Secure transport
----------------
../qseecom-tee-6.18.2-experimental.patch is relative to the current aura kernel
source. It adapts wrobelda/linux commit
662435b853d865d360507f5daee6ff309838c5ca, retaining its GPL notices.
The exact reference diff and GitHub metadata are in sources/qseecom-reference.
The isolated build is /var/tmp/aura-qseecom-6.18.2/{linux,out} in WSL.

Local additions implement the stock 32-bit cmnlib service-image command
(QSEE_OS / APP_MGR / 0x07), on an explicit privileged app-load request only.
SCM caches a successful service load until reboot. No shared service unload
is exposed. Firmware comes from request_firmware(), never arbitrary uploaded
buffers. Both app and service staging reject ELF64 and non-little-endian ELF.
The captured device tree only explicitly declares cmnlib64 preloaded; whether
cmnlib is already present at boot still requires hardware confirmation. A
rejected service load is returned as an error, not ignored or called success.

Reviewed fixes cover session-close/invoke races, app-lookup/load publication,
failed session reference cleanup, and shared-memory error-pointer handling.
This is not a complete security audit. The reference listener machinery can
still leave secure world stuck after some protocol errors. First tests require
physical recovery availability. Keep TEE device nodes restricted to root.

The kernel has been fully linked and packaged as v26-qseecom-test with the
repaired v25 low-battery guard. On-phone validation on 2026-10-09 passed:
the root-only TEE interfaces appeared, signed firmware loaded, and one stock
build-info command returned valid text. The diagnostic exited successfully,
with Phosh, SSH and the battery guard still active. Evidence:
test-runs/snapshot/qseecom-first-boot.txt and fpc-build-info-result-retry.txt.
The firmware build identifies FPC1140/FPC2050, but this is a compiled firmware
configuration, not a physical sensor ID. See enrollment bring-up below for
the current development state.

tools/pack_fpc_resources_boot.py adds only the reset/IRQ DT nodes to that
verified boot image, checking every existing DT property is unchanged. The
module preserves reset at probe and only pulses it after a root sysfs write.
The resource image is installed and verified on boot
2c889bc4-ae69-4022-8208-a59a056e53f5. USB access resumed once boot completed.
The module bound, one explicit reset produced a rising IRQ, and stock sensor
command (10,4) returned transport/status zero. The IRQ settled low afterward.
Evidence: test-runs/snapshot/fpc-resources-desktop-check.txt,
fpc-reset-first-test.txt, and fpc-sensor-init-result.txt. The controlled touch
test produced a rising IRQ while armed, and returned to IRQ low on disarm.
See fpc-detect-long-final.txt. This does not prove image quality or matching.

Diagnostic
----------
tools/build_fpc_probe.sh builds build/kali/fingerprint/aura-fpc-probe for ARM64.
Default / --inspect only checks the client device implementation/capabilities.
--load-build-info explicitly loads fpctzappfingerprint through /dev/teepriv0,
opens a client session on /dev/tee0, and sends exactly one metadata command.
It closes both sessions on completion and on error. There are no enroll/delete
commands, arbitrary command input, or template access.

--sensor-init sends only the stock initialization/release command (10,4).
--finger-detect-test initializes, arms stock finger detection with (10,2),
waits 60 seconds, then returns to (10,4) before releasing the session. GPIO
events are recorded separately. Arming failure also attempts (10,4) cleanup.
Both modes use the same checked buffers and do not request an image.
--capture-once arms detection, polls IRQ for up to 60 seconds, and requests
one snapshot inside the TA with command (10,3), returning only status. It
always attempts idle cleanup before unloading. The initial hardware test
returned status 3. The stock capture_image function at 0x581c explicitly
re-arms and retries this status up to ten times; --capture-test implements
that bounded sequence, with a shared 60-second polling budget. Other error
statuses stop the test. No image export or enrollment command is sent.
See test-runs/snapshot/fpc-capture-disassembly.txt for the stock sequence.
Hardware validation succeeded on the second attempt: status 3, then status 0,
followed by successful idle cleanup and IRQ low. No image was exported or
saved, and no fingerprint was enrolled. Evidence:
test-runs/snapshot/fpc-capture-retry-result.txt. This proves the secure capture
path returns success; image quality and matching still need enrollment tests.
The current binary is af5e45e96471f5793d4185c7580ad7df1c1e060e9b9b04fee9ecc6ad17376b89;
older single-command versions are retained on the phone for reproducibility.

Wire layout is derived from the retained stock fingerprint.sdm845.so:
  fpc_tac_transfer @ 0x6e38: request/response are 64 bytes each; request word0
  holds the shared size; the kernel patches a 32-bit address at offset 4.
  fpc_tee_print_build_info @ 0x54a8 and constant @ 0x7fd0: shared words
  [9, 2, status, 1024], with text starting at byte16. Stock ION rounds the
  1040-byte allocation to 4096 bytes. Our allocation and transfer match that.
Evidence is saved in test-runs/snapshot/fpc-build-info-disassembly.txt.

Local validation
----------------
- Wire fixture and bounded reply tests run with AddressSanitizer/UBSan.
- Link-wrapped TEE tests check actual client ioctl messages and all resource
  cleanup for success, inspection, wrong driver, allocation failure, mmap
  failure, load failure, session failure, invoke failure, invalid response,
  and close failure. They never open real TEE devices.
- Firmware audit compares stock file concatenation against the candidate
  loader using captured fpctzappfingerprint and cmnlib files, without execution.
- Modified kernel objects compile with W=1; final full kernel link succeeds.

Remaining before functional fingerprint support
----------------------------------------------
Validate native enrollment/matching with controlled template storage through
real enroll-and-match tests.
The signed firmware load, build-info, GPIO reset/IRQ and sensor-init commands
have passed on hardware; enrollment and authentication are not yet validated.
Do not substitute a desktop biometric result for a real match.
Then integrate enrollment and authentication with the Linux desktop.
The stock HAL also uses Android Keymaster/Gatekeeper for hardware-auth tokens;
the implementation and validation status are recorded below.

Enrollment bring-up (2026-10-09)
-------------------------------
The root-only aura_fpc_bio diagnostic now has preflight, enroll-test,
check-database and verify-test modes. Its fixed test database lives only at
/var/lib/aura/fpc-test-store/aura-fpc-test.db on the phone; templates and images
are not copied to the PC. An existing database prevents new enrollment.
Verification rejects failed loads, invalid counts/IDs and unexpected IDs.
Exit 0 from verify means a firmware match to the single loaded template;
exit 3 means no match; exit 1 means a diagnostic error. No PAM, fprintd or
lock-screen changes have been made.

Stock protocol evidence: fpc-enrollment-disassembly.txt,
fpc-storage-auth-disassembly.txt and fpc-hal-full-disassembly.txt in snapshots.
Enrollment follows capture -> sample -> finish -> save, with at most 100
samples, 180 seconds of polling and ten stock capture retries per sample.
The launcher serializes tests using flock and imposes a 240-second runtime
limit. Normal completion/error attempts sensor idle before unloading.

The temporary qsee-supplicant filesystem listener is based on upstream commit
36e06680cf7f690fccbdcd07abc2a64c4bb061d8 (BSD-2-Clause). The build script changes
transport errors to terminate rather than automatically re-register. Its
systemd sandbox permits writes only to the root-owned 0700 test directory.
Listeners 10 and 28672 registered successfully. This service is not enabled
at boot; Android secure storage is not mounted or accessed.

Hardware preflight passed: zero resident templates, nonzero enrollment
challenge, empty resident DB initialization, enrollment-session start and
clean unload. No samples were submitted in that preflight. Mock TEE tests under ASan/UBSan passed
successful enrollment, sample rejection, refusal to overwrite an existing
database, positive match, no match, unexpected ID and load failure, in
addition to the preflight cases. These simulated results are not evidence
of real biometric matching.

On-phone app and finalization finding (2026-10-09)
------------------------------------------------
Installed Fingerprint app: GTK UI, explicit Polkit administrator authorization,
live touch/lift progress, match/no-match display, cancellation. Root helper
serializes access and starts the confined aura-fingerprint-storage listener
on demand. Cancellation passed on hardware with IRQ idle and no template.
The listener is static/on-demand, not boot-enabled. No PAM/fprintd changes.

Stock capture statuses 1 and 4 request a new touch. Ten consecutive status-3
captures are converted to that same retry result, matching the stock HAL at
0x5b00. Mock tests cover these cases, cancellation, positive/negative matching,
bad-ID and load failures. See tools/build_fpc_bio.sh and tests/test_fingerprint_ui.py.

The user's latest app test accepted all required samples (24 submissions,
last status 0 with remaining 0). Finish enrollment (11,2) returned -1; no
database file was created. Evidence: fingerprint-app-v2-progress.txt.
Offline stock firmware analysis explains a required missing dependency:
fpc_ta_bio_command_handler calls fpc_enrollment_allowed at 0x2ae8 before
fpc_db_add_fingerprint. It requires initialized hardware authentication and
a valid challenge-bound authorization token. Do not fabricate a token or claim
enrollment/matching succeeded before hardware validation.
Gatekeeper driver export initially required explicit approval; the user then
approved copying vendor program code, and the copy completed successfully.
Local driver SHA256: f3d4603ddf6ea0acf7c6448b8dac97b4236389c4ae9d2a7f805ee4d86a03b5af.

Secure enrollment setup update (2026-10-09)
-----------------------------------------
Resident keymaster64 request 0x205/type 2 and FPC wrapped-key initialization
(3,5) passed on real hardware: fpc-auth-preflight-result.txt. Wrapped key bytes
are not saved or logged. The app now offers Set up secure enrollment with a
masked PIN field. A separate Linux Gatekeeper user ID 1000 uses stock commands
0x1001/0x1002; Android primary user ID 0 is not modified. The first setup chooses
its PIN, subsequent operations verify that PIN. Screen-lock PIN is independent.
Only the opaque handle is saved, root 0600 in the private test directory.
PIN travels through stdin, never argv/logs; core dumps are disabled. A verified
69-byte, version-0, challenge-bound HAT is sent to FPC (3,3), not logged/saved.

Local ASan/UBSan simulations pass the full setup flow, secure enrollment
rejection, mismatched challenge rejection and FPC authorization rejection.
Wire tests reject malformed bounds and throttle replies without retries.
Six UI tests cover truthful success/failure/cancellation reporting. These are
simulated checks, not proof that Gatekeeper setup works on this phone.
App v3 installed and opened. Real setup reaches wrapped-key initialization and
challenge acquisition, but Gatekeeper PIN enrollment returns -30. No handle
or fingerprint database was created. See fingerprint-app-v3-result.txt.
Enrollment saving, matching and desktop unlock remain unverified. No raw
image was exported. The user explicitly approved both helper libraries after
the initial auto-review rejection; both copies completed successfully.
Offline analysis confirmed field offsets and revealed stock initialization:
0x200 reads public versions, 0x207 negotiates protocol with words [4,5,4,5,0].
Both steps now pass on hardware (API 3.0, TA 3.132), but initial PIN enrollment
still returns -30. No missing-listener warning appeared in the kernel log.
The next correction matches the stock variable request lengths (32 + PIN
length, or 32 + handle length + PIN length), instead of padded 1024-byte
requests; local simulations cover the exact lengths. Hardware still returns
-30 after that correction (fingerprint-app-v5-result.txt).

Protected storage investigation (2026-10-09)
-------------------------------------------
Bounded signed keymaster_b program copied for offline analysis (232947 bytes,
SHA256 1faa5227cecb7a3591a95118476aefa05dea01f0e4a479372621069546068f06).
No secure user storage was copied. Its enrollment parser matches our fields.
One -30 path is enroll 0x139a4 -> gk_get_rpmb_data_uid 0x1db60 returning NULL
-> 0x13b88. That helper calls gk_rpmb_init 0x1e2c8, which uses imported
qsee_stor_read_sectors / write_sectors. Other error paths exist; this offline
finding alone does not establish the exact runtime cause.

Linux has CONFIG_SCSI_UFS_BSG=y and /dev/bsg/0:0:0:49476. Public descriptor
reads succeeded: UFS 2.10, 32768 sectors of 512 bytes (16 MiB), transfer limit
64 frames. CONFIG_RPMB=n does not remove this existing BSG transport.
The regular qsee-supplicant supports only FS and GPFS, not RPMB listener 8192.
Qualcomm's public minkipc listener supplies the protocol reference; sources
are retained in sources/minkipc-reference (see its licensing headers).

Built a separate bounded read-only diagnostic listener, rejecting all RPMB
write requests with EROFS and rejecting key-provision frames. No frame data
is logged. ASan/UBSan tests cover bounds, prohibited operations and mocked
counter reads. Native descriptor query passed. The diagnostic listener uses a /run
systemd override, with CAP_SYS_RAWIO for BSG. It disappears on reboot or via
diagnostic/kali-rpmb-readonly-stop.sh. Regular packaged listener is unchanged.
The 05:41:19 UTC PIN setup test confirmed two successful 24-frame reads,
followed by a two-frame write deliberately rejected with EROFS (-30).
See rpmb-readonly-result-latest.txt. No payload data was logged.

Authenticated-write relay built and activated at 05:46:29 UTC. Only intact
single-transaction type-3 frames from secure firmware are accepted; frame
counts, offsets, address/counter consistency and device bounds are checked.
Key provisioning is always rejected. No key/MAC generation or modification,
storage reset or write retries. Device result is returned to secure firmware
unchanged for verification. ASan/UBSan mocked tests cover 1/2-frame writes,
preservation of frames, malformed requests and failures at each SCSI stage.
Build: tools/build_rpmb_authenticated.sh; binary SHA256:
5b515613e73cd70c574d8342547269c8722b994c0cd953a593e8f73148324a1b
The existing runtime override now points to this binary with core dumps
disabled. Same rollback script restores filesystem-only listener support;
it cannot undo authenticated records already committed by secure firmware.
Hardware setup validated at 17:09:58 UTC: four authenticated two-frame writes
completed, Gatekeeper PIN enrollment and verification returned 0, and FPC
accepted the genuine authorization token. Private handle is 58 bytes, mode
0600; contents not exported. User saw "Secure enrollment is ready". Evidence:
fingerprint-secure-ready.txt and rpmb-authenticated-result.txt. Fingerprint
template saving and same/different-finger matching still require validation.

Persistent app bundle v6 is prepared and staged, SHA256:
f090e736dc48c47a0bc904de14f5a0e5ff730fed2da6e51e5d2906399d8a4a32
It packages the verified RPMB binary and updates the on-demand service with
CAP_SYS_RAWIO and LimitCORE=0. It is NOT installed: automatic approval review
requires explicit user approval for this persistent privileged configuration.
Phone still runs v5 app plus the runtime-only RPMB override. Approval pending.

Enrollment and reload correction (2026-10-09)
--------------------------------------------
Authorized enrollment completed at sample attempt 21: finish=0, one template
listed, save=0. Private database exists only on phone, 68637 bytes, root 0600.
The UI's subsequent reload check failed although load itself returned 0.
Stock HAL 0x3a98 loads the database, then 0x3ad8 selects the active group. Our
verification path omitted that second step. Adding group UID 1000 after load
fixed the real-device fresh-session check: DATABASE_RELOADED, one template.
No re-enrollment, deletion or export was needed. Native backend was updated
separately (not the blocked persistent service) and installed check passed.
Native SHA256 b0dcfc7ccdd4c946c9a6643892de4affcb37dfbe5d0ae88b5f33f6a9ef9716de
ASan/UBSan regressions include reload-only mode, empty database rejection,
group-selection failure, match/no-match and wrong-ID rejection. Real matching
awaits the user's same/different-finger tests. Desktop unlock remains disabled.
Matching validation: user confirmed enrolled-finger match and different-finger
rejection. Latest native log independently confirms NO_MATCH / UI_NO_MATCH,
successful capture/identify, clean idle and preserved private template file.
Evidence: fingerprint-matching-confirmed.txt. One match/rejection pair verifies
basic operation only; no broader biometric accuracy/security claim is made.
Desktop authentication remains unchanged and disabled for fingerprints.

Persistent bundle rebuilt with the verified reload correction, superseding
the old staged v6 bundle. Current local SHA256:
73dbe41751c8f7d8aa350d31165b9867762e173d65cfc789063d75bc5410f461
After explicit user approval, this bundle was installed at 20:27:25 UTC.
Permanent unit lives in /etc/systemd/system; runtime override removed and
service restarted. Saved template reload passed again. Core dumps disabled;
CAP_SYS_ADMIN/CAP_SYS_RAWIO restricted to the listener. The app starts it on
demand, including after reboot; it is not automatically enabled at boot.
Full phone reboot was not performed. Desktop unlock remains disabled.
Evidence: fingerprint-permanent-install.txt. Original service unit backed up
on phone at /var/lib/aura/fingerprint-storage-before-permanent.service.
Explicit rollback: diagnostic/kali-fingerprint-storage-rollback.sh restores
that service only; it does not delete templates or undo secure-storage writes.
The older kali-rpmb-readonly-stop.sh now only removes a temporary override;
it is not a rollback of this permanent installation.

Independent fixed counter-query probe passed on real hardware: response type
0x0200, result 0, fresh nonce matched. No counter value/MAC/record contents were
logged. This confirms the read transport responds; it does not verify the MAC
(that stays the secure firmware's responsibility). See rpmb-counter-check.txt.

Raw-image inquiry: engineering module 6 is present in this signed DEBUG build.
Decoded command table: 1 retrieve (type 0 raw / 1 enhanced, size at 16, output
at 20), 2 sensor info, 3 inject (NOT to be exposed), 4 raw size. These are
offline observations, not proof of on-device export. No raw image has been
retrieved or saved. Any future UI export must be explicit and local to phone.
See fpc-ta-engineering-disassembly.txt and fpc-ta-enrollment-disassembly.txt.
