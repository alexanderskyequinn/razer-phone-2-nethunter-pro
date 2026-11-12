"""Record measured peripheral progress without treating discovery as validation."""
import json
from datetime import datetime, timezone
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'port-status.json'
data=json.loads(path.read_text())
data['hardware_progress']={
    'updated_utc': datetime.now(timezone.utc).isoformat(),
    'booted_version': 'v11, Linux build #9; installed and booted successfully, slot B marked successful by qbootctl.',
    'installed_image': 'aura-kali-trial-v11.img SHA256 17e689849764534f52f9bf0d78244103e95f4c33e0c13eae56847c9b214c5ac4. Contains NFC DT and persistent sensor startup/mounting correction.',
    'verified': {
        'haptics': 'User felt all three test pulses; original 1.3 V limit enforced by driver.',
        'rotation': 'User confirms correct portrait and landscape after v11 reboot. Patched startup service and diag(-1,-1,1) mounting correction persist. User reports brief black screen during rotation; compositor logs full modeset on transition, smoothness remains unresolved.',
        'nfc_controller': 'Basic ISO14443 tag detection verified after reboot: TAG DETECTED protocols=0x10, then clean controller power-down. Cash App card independently detected by S23 Ultra/NFC Tools Pro. Applied upstream parser fix 571dcbeb8e635182bb825ae758399831805693c2 after observing a 39-byte activation notification rejected by the old sizeof check. Installed nci module 8428205815223513e4b2854ce10a3850c7b13d85038585d1aa92ea243fafb31b, nxp-nci module 54ea3d0530b5907622c56ad2f83d1e9c1668b1009c27523c0cdbb43b2987efd1, I2C module 45c60017a472b33a0f124dc1324601bb817cb5dbd1b13ab22f5e460b066efd1d and config be86e86d8266225ef80f98b3e2b0c370b5d6f7b84535e4ab9d9c97f3375283cf. Three start/stop cycles passed. Read/write, other protocols and emulation remain untested. No card contents read or controller firmware downloaded.',
        'bluetooth': 'User paired and connected a device; controller sleep disabled as an experimental workaround, suspend/power consumption unvalidated.',
        'speakers': 'User confirmed clear tone after Razer-specific 24-bit / 3.072 MHz clock lifecycle fix. Persistent UCM corrected to establish routes before probing; desktop silent playback passes after reboot.',
        'microphone': 'Internal capture detects acoustic 440 Hz speaker tone on both PCM channels; independent physical channels not established. Desktop recording works; startup clipping/transients and voice quality remain to characterize.',
        'magnetometer': 'libssc returns live 3-axis measurements; calibration and compass accuracy unverified.',
        'adsp_slpi': 'Original firmware starts both DSPs successfully.'
    },
    'detected_not_functionally_verified': ['microSD controller', 'volume-down input', 'Venus video processor'],
    'blocked': {
        'wifi': 'Modem firmware crashes shortly after startup; no WLAN QMI service. One-shot trace confirms successful reads of modemst1/2 using corrected stock buffer 0xf5a01000, matching original Android read sequence. Crash persists after bulk read; missing OEM FSG requests are rejected but not established as cause. Temporary verbose tracing ended at reboot. User-approved temporary retry pause reapplied after NFC board-config reboot; modem reported offline.',
        'sensor_restart': 'Old sensor process took about one minute to exit while QRTR socket cleanup waited on crashed-modem GLINK. It eventually exited and patched service started successfully. Separate live SLPI restart previously timed out; full reboot recovered DSP.',
        'modem_recovery': 'With explicit user approval, automatic retries disabled for current boot by resolving modem remoteproc by name. Modem now remains crashed. Reboot restores recovery; no new persistent recovery policy applied.',
        'light_proximity': 'libssc initialization returns UNKNOWN.',
        'restart': 'Some restarts stall even with systemctl reboot --force; physical bootloader restart needed.'
    },
    'not_ported': ['logo LED', 'cameras', 'fingerprint', 'USB host/type-C roles', 'wireless charging integration'],
    'evidence': ['test-runs/kali-trial-v9/haptics-test-repeat.txt', 'test-runs/kali-trial-v10/bluetooth-trace-v11.txt', 'test-runs/kali-trial-v10/audio-test-clock-fixed.txt', 'test-runs/kali-trial-v10/mic-acoustic-check.txt', 'test-runs/kali-trial-v10/audio-desktop-check.txt', 'test-runs/kali-trial-v10/sensor-hang.txt', 'test-runs/kali-trial-v10/hardware-after-reboot-retry.txt'],
    'usb_connection': 'User confirms mechanically flaky phone USB port; movement can disconnect USB while Kali remains running.',
    'unapplied_change': 'Earlier persistent modem recovery/coredump hook correction remains unapplied. User later approved current-boot-only disabling of modem retries; applied successfully.',
    'motion_test': 'Recording retrieved and stopped after user completed the movement test. X range -18.390253..15.903725, Y -16.878693..11.234895, Z -25.468956..27.464407 m/s2 (including movement transients). Median segments include all six signed dominant axes. Desktop orientation monitor also records four orientations. Evidence: motion-capture.txt, rotation-reclaim-retry.txt and rotation-restarted-debug.txt under test-runs/kali-trial-v10.',
    'nfc_candidate': 'Generic NXP NCI driver, I2C3 address 0x28, VEN GPIO12, FW GPIO62, IRQ GPIO63 and stock PM8998 GPIO21 clock-request pin. Cold IRQ/probe cleanup patch port/nxp-nci-cold-irq.patch installed; three power cycles pass after reboot. Avoid live module reload: DT level-high versus driver forced rising causes IRQ remapping failure on reload. Future DT should match rising trigger.',
    'bluetooth_backup': 'User declined Bluetooth maintenance access; keep USB-only. Proposed service was never installed. Removed its sources from overlay and installer from project to prevent accidental inclusion in future builds.',
}
data['hardware_progress']['blocked']['display_modeset'] = 'During latest NFC test, DPU interrupt callback warnings occurred in phoc modeset path around boot second 107, before NFC activation at second 120. Desktop remained active. Rotation/display power transitions require further investigation; evidence nfc-final-health.txt.'
data['hardware_progress']['evidence'] += ['test-runs/kali-trial-v11/nci-parser-card-result.txt', 'test-runs/kali-trial-v11/nci-parser-three-cycles.txt', 'test-runs/kali-trial-v11/nfc-final-health.txt']
data['status']='Native Kali/Phosh and NetHunter GUI on persistent root with GPU, touch, keyboard, USB SSH, portrait/landscape rotation, haptics, Bluetooth pairing, clear speaker playback, measured internal microphone capture and basic ISO14443 NFC card detection. Remaining hardware support experimental/incomplete.'
data['kali_image']['limitations']=['Wi-Fi blocked by modem crash', 'Rotation works with brief black transition; DPU modeset warnings and light/proximity unresolved', 'Basic ISO14443 NFC detection verified; data read/write, other protocols and emulation not validated', 'Bluetooth sleep disabled; suspend and power usage unvalidated', 'Audio basic playback and capture work; long-term operation and capture quality not fully validated', 'Sustained charging and remaining peripherals not fully validated']
path.write_text(json.dumps(data,indent=2)+'\n')

# Radio startup milestone supersedes the earlier crash investigation above.
progress = data['hardware_progress']
for key in ('wifi', 'modem_recovery'):
    progress['blocked'].pop(key, None)
progress['verified']['modem_startup'] = 'Razer FIH NV buffer 0xaf000000/8MiB must be shared RW with HLOS and MSS_MSA before MBA, matching stock loader. Installed qcom_q6v5_mss module c31cf4a2947cd38e479830ddb84cd1f566b2da07c4251537c0137ab0fcc40329. Modem remains running with automatic recovery enabled, exposes QMI services and accepts online mode. ModemManager 1.24.2 recognizes qrtr0 and rmnet_ipa0; currently reports sim-missing/no ATR. Carrier registration, calls and mobile data untested.'
progress['verified']['wifi_scan'] = 'WCN3990 WLAN.HL.2.0.c10-00085 firmware initializes after Razer-specific HOST_CAP skip matching stock ICNSS; preceding command caused MSA_INFO QMI error 90. Installed ath10k_snoc efcb5524756c15bc6b0cd35c6d1e95cb194789c295065184d70c7fb0db0f2526. wlan0 scans 2.4/5GHz networks via NetworkManager. Association and internet test await user. Firmware returns invalid MAC and driver generates random address; permanent address integration remains.'
progress['blocked']['cellular_validation'] = 'ModemManager reports SIM missing/no ATR; awaiting whether an active SIM is installed.'
progress['evidence'] += ['test-runs/kali-trial-v11/modem-nv-health.txt', 'test-runs/kali-trial-v11/wifi-startup-first-boot.txt', 'test-runs/kali-trial-v11/wifi-first-scan.txt', 'test-runs/kali-trial-v11/modem-online.txt']
progress['radio_package'] = 'build/kali/radio-startup-fix.tar and JSON manifest; source patches port/razer-modem-nv-memory.patch and port/razer-wifi-startup.patch; original modules backed up on phone.'
data['status'] += ' Modem startup crash fixed and Wi-Fi scanning verified; association and cellular service validation pending.'
data['kali_image']['limitations'][0] = 'Wi-Fi scanning works; connection/data test pending. Modem runs and is recognized but no usable SIM detected; cellular service not validated.'
progress['booted_version'] = 'v12, Linux build #10; installed from Kali to boot_b with preflight identity/partition/hash checks, readback verified, booted successfully; slot B remains successful.'
progress['installed_image'] = 'aura-kali-trial-v12.img SHA256 e4f962ad442ec22a7f46500bd7d16467b48d97eef84008a6a07e4b8cb4c2cecb. Same v11 DT and sensor overlay, DPU IRQ indices preserved through resource disable.'
progress['verified']['display_irq_lifecycle'] = 'Removed premature IRQ index clearing in physical encoder disable; resource shutdown now unregisters the correct callbacks. Four software rotation transitions and immediate rotation plus screen off/on passed on v12; trace confirms PRE_OFF path unregisters/re-registers correctly, no invalid IRQ, duplicate callback or commit timeout warnings. Perceived automatic rotation black pause still awaits user comparison.'
progress['blocked']['display_modeset'] = 'IRQ lifecycle defect fixed and controlled regression tests pass; visual smoothness of automatic rotation awaits user confirmation.'
progress['verified']['rotation'] = 'Portrait/landscape and mount correction previously user-verified. v12 preserves sensor binary and configuration. Controlled rotations pass; user comparison of black transition remains pending.'
progress['evidence'] += ['test-runs/kali-trial-v12/first-boot-health.txt', 'test-runs/kali-trial-v12/display-mode-transition-test.txt', 'test-runs/kali-trial-v12/display-power-test.txt', 'test-runs/kali-trial-v12/modem-after-startup.txt']
data['kali_image']['limitations'][1] = 'Rotation works; display interrupt shutdown defect fixed and controlled tests pass. Visual black pause comparison and light/proximity remain unresolved.'
progress['verified']['wifi_connection'] = 'User confirms Wi-Fi works and connects. wlan0 associated, DHCP address/default route obtained, gateway and public IP ping pass. Fixed stale WSL /etc/resolv.conf by linking NetworkManager resolver; DNS and HTTPS to www.kali.org return HTTP/2 200 over wlan0. SSH still listens only on 192.0.2.1:22.'
progress['blocked']['cellular_validation'] = 'User has no active SIM available. Modem startup and QMI discovery verified; carrier registration, calls and mobile data untested.'
progress['blocked']['display_modeset'] = 'User reports black rotation pause arguably worse on v12 despite corrected kernel IRQ lifecycle. Phoc logs 3000ms layout transaction timeouts and uses a black modeset shield on transform changes. Preparing opt-in live rotation in the same compositor version; not yet installed.'
progress['evidence'] += ['test-runs/kali-trial-v12/wifi-connected-verified.txt', 'test-runs/kali-trial-v12/wifi-dns-fixed.txt', 'test-runs/kali-trial-v12/real-rotation-trace-start.txt']
data['kali_image']['limitations'][0] = 'Wi-Fi connection and HTTPS verified. Cellular service awaits an active SIM; modem startup works.'
data['kali_image']['limitations'][1] = 'User reports worse black rotation pause on v12; compositor layout wait under investigation. Light/proximity unresolved.'
progress['desktop_rotation_candidate'] = 'Phoc 0.58~alpha1-1 rebuilt with original distribution patches plus opt-in PHOC_AURA_LIVE_ROTATION=1 to avoid raising a black layout shield for transform commits. Binary ccfb6e64234feb22a9e5a58f044783bcd91b70670ea758883b3ae35ab623e48b running from /usr/local/libexec/aura-phoc via temporary /run service override. Three existing regression tests pass; GPU acceleration and connected Wi-Fi retained. User estimates original pause at half a second; visual comparison of candidate pending. Packaged phoc unchanged; build/kali/phoc-live-rotation.tar and JSON preserve exact candidate.'
progress['blocked']['display_modeset'] = 'Kernel IRQ lifecycle corrected. Half-second visible rotation pause remains under user evaluation with the temporary live-rotation compositor candidate; do not call it fixed yet.'
data['status'] = 'Native Kali/Phosh and NetHunter on persistent v12 root with GPU, touch, keyboard, USB SSH, Wi-Fi association and HTTPS, portrait/landscape rotation, haptics, Bluetooth pairing, speaker playback, microphone capture and basic NFC detection. Modem startup crash fixed; cellular service awaits an active SIM. Rotation pause candidate under evaluation; other peripherals incomplete.'
progress['desktop_rotation_candidate'] = 'First live-rotation candidate reduced the black pause to occasional ~100ms but briefly exposed half-screen app layouts; user confirms layout corrects quickly. Superseded by temporary retained-frame crossfade candidate /usr/local/libexec/aura-phoc-crossfade SHA256 12c47e799a482fed557a8d671f9cd2b959fadcd19c9fc71a87d95a855486b35d. Holds complete physical frame for visible client resize (max 300ms), then 150ms smoothstep crossfade; no angular rotation animation. Four existing regression tests and a new render-level delayed-resize/overlay-precedence test pass. Running on phone with GLES2/Adreno and connected Wi-Fi. User visual test pending; packaged compositor unchanged and runtime override disappears on reboot.'
progress['blocked']['display_modeset'] = 'Kernel IRQ lifecycle corrected. Live rotation improved pause but exposed transient incomplete layout. Retained-frame crossfade now running temporarily; awaiting user assessment, not yet a verified visual fix.'
progress['evidence'] += ['build/kali/phoc-crossfade-render-test.log', 'test-runs/kali-trial-v12/phoc-crossfade-running.txt']
data['kali_image']['limitations'][1] = 'Rotation works; temporary crossfade candidate under visual evaluation. Light/proximity unresolved.'
progress['verified']['cpu_performance'] = 'All 8 cores online. Stock CPU boost was disabled (2.6496 GHz policy limit); enabled existing 2.8032 GHz boost OPP and verified this speed with a two-second governor ceiling test, then restored schedutil. aura-cpu-boost.service now enabled persistently. No voltage/clock table changes or thermal bypass. User reports noticeably better app launches/swiping. Sustained maximum clock endurance untested.'
progress['verified']['gpu_performance'] = 'FD630/Freedreno hardware rendering confirmed in benchmark and app DRM engine counters. GPU sampled at 710 MHz. Correctly sized windowed vsync benchmark delivers 120 FPS; 478 delivered vblank events median 8.31ms. Off-screen scenes 424 and 500 FPS. Baseline no cooling limits or memory pressure; storage direct read 259 MB/s. Not a guarantee of smoothness in all applications.'
progress['verified']['keyboard'] = 'Replaced Squeekboard as selected OSK with official phosh-osk-stevia 0.57.0-2. User confirms rapid app switches now hide keyboard correctly. Persistent /etc/systemd/user/mobi.phosh.OSK.service.d/30-aura-stevia.conf selects Stevia, temporary runtime override removed; original Squeekboard retained for rollback.'
progress['desktop_performance_package'] = 'build/kali/desktop-performance-fix.tar and JSON, plus build/kali/stevia-packages. Package recipe and existing local image-build root updated. Persistence configuration verified; not reboot-tested this turn.'
progress['evidence'] += ['test-runs/kali-trial-v12/cpu-stock-ceiling.txt', 'test-runs/kali-trial-v12/presentation-trace.txt', 'test-runs/kali-trial-v12/desktop-performance-persistent.txt']
data['status'] += ' Stock CPU boost enabled and measured at 2.8032 GHz; GPU 710 MHz and 120 FPS presentation verified. User reports improved responsiveness and confirms Stevia fixes stuck keyboard; both settings persistent.'
# Persistent desktop milestone supersedes temporary candidate notes above.
progress['desktop_rotation_candidate'] = 'User-approved crossfade now persistent through /etc/systemd/system/phosh.service.d/30-aura-crossfade.conf, selecting separate binary /usr/local/libexec/aura-phoc-crossfade SHA256 12c47e799a482fed557a8d671f9cd2b959fadcd19c9fc71a87d95a855486b35d. Temporary override removed; packaged compositor preserved. Exact binary, option and GLES2 verified after reboot. Source, launcher, configuration and regression test saved in build/kali/phoc-crossfade.tar; local image recipe/root updated, full rootfs image not regenerated.'
progress['verified']['rotation'] = 'User confirms retained-frame crossfade looks good. Sensor mounting and crossfade configuration persist; running compositor and option verified after reboot a7517520-8076-4a4b-8de7-dd5ce9acce16. After reboot user confirms rotation is good enough, with some sluggishness remaining.'
progress['verified']['display_irq_lifecycle'] += ' Latest reboot health check found no matching kernel IRQ/timeout warnings.'
progress['blocked'].pop('display_modeset', None)
progress['blocked']['restart'] = 'Latest normal reboot succeeded without requested manual reset, but SSH returned only after roughly two minutes. Earlier stalls mean reboot latency/reliability and suspend still require investigation.'
progress['verified']['wifi_connection'] += ' Association, resolver and HTTPS HTTP/2 200 reverified after persistent desktop reboot.'
progress['verified']['wifi_scan'] = 'WCN3990 Razer-specific HOST_CAP fix installed; 2.4/5GHz scanning and user connection verified, with HTTPS also passing after reboot. Firmware returns invalid MAC and driver generates random address; permanent address integration remains.'
progress['verified']['cpu_performance'] += ' After reboot boost=1, policy maximum 2803200 kHz and schedutil verified.'
progress['verified']['keyboard'] += ' Active Stevia process and persistent drop-in verified after reboot; final physical app-switch check pending.'
progress['desktop_performance_package'] = 'build/kali/desktop-performance-fix.tar and JSON, plus build/kali/stevia-packages. Package recipe and existing local image-build root updated. CPU boost and Stevia startup verified after reboot.'
progress['reboot_validation'] = {'boot_id': 'a7517520-8076-4a4b-8de7-dd5ce9acce16', 'previous_boot_id': '6d5efdcc-5783-4429-997b-e639e9bd37b2', 'result': 'Persistent crossfade, GLES2 renderer, CPU boost, Stevia, Wi-Fi HTTPS and modem/ADSP/SLPI startup pass. SSH listens only on USB 192.0.2.1:22. No failed system units. Display 1440x2560 at 119.802 Hz. This does not validate suspend, cellular service or sustained performance.'}
progress['evidence'] += ['test-runs/kali-trial-v12/crossfade-persistent.txt', 'test-runs/kali-trial-v12/crossfade-reboot-health-final.txt']
data['status'] = 'Native Kali/Phosh and NetHunter on persistent v12 root. User-approved rotation crossfade, CPU boost and Stevia now persistent and startup verified after reboot; rotation accepted after reboot with some sluggishness. Wi-Fi HTTPS and GPU rendering retained. Modem startup works; active Verizon SIM inserted; cellular validation underway. Remaining hardware and suspend/reboot reliability incomplete.'
data['kali_image']['limitations'][1] = 'Crossfade looks good per user and persistent startup verified after reboot; user accepts post-reboot rotation with some sluggishness. Light/proximity unresolved. Crossfade does not guarantee every client resizes within its bounded hold.'
# Active Verizon SIM milestone; keep data validation separate from IMS voice/SMS.
progress['verified']['modem_startup'] = 'Razer FIH NV sharing fix retains healthy modem startup. Active Verizon SIM recognized after one standard UIM slot-1 power refresh cleared an anomalous 0x4e card state following hot insertion. PIN1 disabled; no PIN attempts or SIM content edits. ModemManager now registers home on Verizon LTE and establishes a vzwinternet IPv4v6 bearer.'
progress['verified']['cellular_data'] = 'HTTPS HTTP/2 200 first verified with socket bound to qmapmux1.0. Initial connection then detached and attempted another carrier. Standard EPS PS-2 request reported a verification error but NAS readback confirms ps-only/data-centric applied; radio low-power/online refresh restored LTE. Afterward default route, DNS and HTTPS all passed with Wi-Fi disabled, then Wi-Fi restored. User confirms LTE browsing. Seven cellular HTTPS requests pass over 183 seconds with continuous home registration; reboot persistence check underway.'
progress['verified']['resolver'] = 'Existing /etc/resolv.conf link targets /run/NetworkManager/resolv.conf. Added 91-aura-resolver.conf with dns=default and rc-manager=symlink to avoid failing resolvconf auto-selection; reloaded without NetworkManager restart. Overlay and local build root updated.'
progress['blocked']['cellular_validation'] = 'Verizon LTE data now functionally verified; three-minute stability passes and reboot persistence is under evaluation. IMS registration/services queries return InvalidOperation; calls, SMS and emergency calling not established.'
progress['cellular_profile'] = 'Verizon Internet, APN vzwinternet, IPv4v6, metered=yes, home-only=yes, automatic connection enabled, route metrics 700. Remote SSH remains USB-only.'
progress['evidence'] += ['test-runs/kali-trial-v12/sim-protocol.txt', 'test-runs/kali-trial-v12/sim-power-refresh.txt', 'test-runs/kali-trial-v12/sim-ready-status.txt', 'test-runs/kali-trial-v12/verizon-cellular-https.txt', 'test-runs/kali-trial-v12/cellular-drop-events.txt', 'test-runs/kali-trial-v12/cellular-mode-result.txt', 'test-runs/kali-trial-v12/cellular-only-verified.txt']
data['kali_image']['limitations'][0] = 'Wi-Fi and Verizon LTE data verified, including DNS/HTTPS with Wi-Fi off. Cellular stability/persistence under evaluation; IMS voice and SMS not established.'
progress['verified']['cellular_data'] = 'User confirms browsing with Wi-Fi off. Seven interface-bound HTTPS checks passed over 183 seconds with uninterrupted Verizon home LTE registration. Final boot e7060155-1d1b-422b-a45a-f1deb80710f3 recognizes SIM present/ready, applies data-centric/packet-only preferences after modem initialization, automatically connects Verizon Internet and returns HTTP/2 200 through qmapmux0.0 with Wi-Fi off. This is short functional/reboot validation, not long-term endurance.'
progress['blocked'].pop('cellular_validation', None)
progress['blocked']['ims_voice_sms'] = 'LTE data works. IMS registration/service queries returned InvalidOperation; voice, SMS and emergency calling not established. IMS integration remains separate work.'
progress['cellular_startup'] = 'aura-modem-data-mode.service is WantedBy/After/PartOf ModemManager. Python wrapper waits for initialized modem state; Razer-only libqmi helper waits for NAS advertisement, sets volatile data-centric and packet-only preferences and polls delayed readback. Running before modem initialization was insufficient because later defaults overwrote it. Binary SHA256 9abbc20e73681cd1ee6dcc8e7b08eda5d92f2db60269c18def15669cd815e227. Final boot service succeeds. Absent/locked SIM is skipped; restart service after SIM setup. No SIM PIN attempts, identity edits or band changes.'
progress['cellular_package'] = 'build/kali/cellular-startup-fix.tar plus cellular-progress.json; includes helper, wrapper, service, resolver config and C source. Local build root and recipes updated with ModemManager/libqmi-utils dependencies. Carrier connection is saved on phone, not baked into generic image. No full rootfs image regenerated.'
progress['evidence'] += ['test-runs/kali-trial-v12/cellular-persist-reboot.txt', 'test-runs/kali-trial-v12/data-mode-after-sim-installed.txt', 'test-runs/kali-trial-v12/cellular-final-reboot-verified.txt']
data['kali_image']['limitations'][0] = 'Wi-Fi and Verizon LTE data verified; user browsing, short stability and automatic reconnection after reboot pass. IMS voice/SMS and long-term mobile-data endurance not established.'
data['status'] = 'Persistent native Kali/Phosh and NetHunter v12. Rotation accepted with some sluggishness. CPU boost, Stevia and GPU verified. Active Verizon SIM now supports LTE data: user browsing, DNS/HTTPS with Wi-Fi off, three-minute stability and automatic setup/reconnection after reboot pass. IMS voice/SMS, suspend/reboot latency and remaining peripherals need further work.'
progress['verified']['telephony_packages'] = 'Official 81voltd 1.2.0-2, gnome-calls 50.0-1 and chatty 0.8.9-2 installed; package audit clean. IMS helper enabled, Calls and Messages desktop services running. Build root and package recipes updated. No full image rebuilt.'
progress['blocked']['ims_voice_sms'] = 'Incoming SMS user test failed. Subscription-0 binding fixes InvalidOperation diagnostics. Direct reads confirm IMS/VoLTE/mobile-data/SMS enable flags; libqmi 1.38 settings getters use incorrect TLV IDs, so earlier SMS-disabled readings were invalid. Correct Verizon profile active and network IMS voice supported. Temporary IMS IPv6 bearer connects and is cleanly removed, but IMSA reports not registered/no IMS PDP. Standard IMS cycle and held control client did not trigger registration. Need further modem IMS initialization tracing; calls and emergency service unvalidated.'
progress['telephony_package'] = 'build/kali/telephony-progress.json, verified offline .deb archive and C diagnostics. See report for library parsing correction and limits; do not infer working voice from installed apps or enabled flags.'
progress['evidence'] += ['test-runs/kali-trial-v12/ims-bound-probe.txt', 'test-runs/kali-trial-v12/ims-complete-enable-flags.txt', 'test-runs/kali-trial-v12/imsa-pdp-probe.txt', 'test-runs/kali-trial-v12/telephony-final-lte-health-retry.txt']
data['status'] += ' Calls, Messages and IMS helper installed; incoming SMS test failed. IMS connection initialization remains under investigation.'
progress['blocked']['ims_voice_sms'] += ' Follow-up direct reads show primary IMS subscription active, LTE allowed and both blocking masks zero. Stock-style event subscriptions accepted, but a 60-second held-client test produced only a settings-change event and no registration/PDP connection. SIM detected state is handled as ready by stock software when PIN1 disabled, as here. LTE HTTPS still passes; final domain observed cs-ps/data-centric, so ps-only is not invariant.'
progress['evidence'] += ['test-runs/kali-trial-v12/ims-active-policy-probe.txt','test-runs/kali-trial-v12/ims-startup-result-final.txt','test-runs/kali-trial-v12/ims-continuation-health-final.txt']
progress.setdefault('deferred',{})['sim_cellular'] = 'User explicitly paused ALL SIM/cellular work; SIM removed. Resume only if requested. Existing LTE/IMS evidence retained.'
progress.setdefault('known_preexisting',{})['front_camera'] = 'User reports front camera inoperable under Android; firmware versus hardware cause unknown.'
progress['verified']['suspend'] = 'Razer no-IBS Bluetooth workaround caused qca_suspend timeout -110. Powering Bluetooth off through BlueZ allows RTC-timed s2idle. Two short sleep/wake cycles passed, second using installed aura-bluetooth-sleep.service; prior powered state restored. User confirms touch, rotation and keyboard after wake. Automatic idle sleep remains disabled. Bluetooth devices disconnect during sleep and cannot wake phone. Long-duration power savings, peripheral reconnection and mobile-data resume with SIM inserted not verified; user confirmed SIM removed during testing.'
progress['blocked']['light_proximity'] = 'Read-only SSC discovery returns 40 sensors; both default/all-match requests show no ambient_light/proximity. Read all advertised names/types: no alias found. Factory persist registry entries match live copies. Missing sensor-path config noted, not modified; root cause unresolved.'
progress['compatibility_package'] = 'build/kali/compatibility-progress.json and suspend-fix.tar/json. Suspend helper installed and enabled, local build root and recipe updated; full image not rebuilt.'
progress['verified']['microsd'] = 'User-inserted64GB SDXC detected as59.5GiB exFAT, UHS-I SDR104/4-bit/1.8V/201.5MHz. Read-only1MiB samples at start/middle/end and ro exFAT mount/unmount passed. No card writes or file listings. Write and endurance testing remain.'
progress['evidence'] += ['test-runs/kali-trial-v14/microsd-read-test.txt','test-runs/kali-trial-v14/microsd-filesystem-test.txt']
progress['evidence'] += ['test-runs/kali-trial-v12/sensor-discovery-attributes.txt','test-runs/kali-trial-v12/sensor-factory-compare.txt','test-runs/kali-trial-v12/suspend-bt-off-result-final.txt','test-runs/kali-trial-v12/suspend-persistent-result-retry.txt']
data['kali_image']['limitations'][3] = 'Bluetooth sleep handshake disabled; temporary power-off/restore across suspend enables two short s2idle tests. Automatic idle sleep remains off; long-term drain and Bluetooth peripheral reconnection unvalidated.'
data['status'] += ' IMS deferred by user. Two short suspend/resume tests pass with Bluetooth power-cycle hook; touch, rotation and keyboard user-verified after wake. Front camera had already failed under Android.'
logo_path = root/'build/kali/logo-progress.json'
if logo_path.exists():
    logo = json.loads(logo_path.read_text())
    if logo.get('boot_version') == 'v14':
        progress['booted_version'] = 'v14; same Linux #10 kernel as v12, corrected logo DT and restored NFC nodes.'
        progress['installed_image'] = 'aura-kali-trial-v14.img SHA256 ' + logo['boot_image']['sha256']
        progress['not_ported'] = [item for item in progress['not_ported'] if item != 'logo LED']
        progress['verified']['logo_controller'] = logo['status']
        progress['blocked']['logo_validation'] = 'All channel colors user-verified and RGB helper readback passes. Spatial green-channel1/2 assignment, color balance and power draw remain uncharacterized.'
        progress['logo_package'] = 'build/kali/logo-progress.json, logo-modules.tar, v14 boot image, logo-app/manifest.json and archive; source and build recipes retained. Logo Light app has user-confirmed Rainbow button; screen-aware rainbow/solid control passes actual display power transitions.'
        progress['evidence'] += logo['evidence']
        data['status'] = 'Persistent native Kali/Phosh and NetHunter v14. GPU, CPU boost, keyboard and accepted rotation retained. Two short suspend tests passed with Bluetooth sleep hook. All nine logo color channels user-verified; RGB control installed and readback tested. All SIM/cellular work paused at user request. Remaining peripherals and long-term power/reboot reliability incomplete.'
wireless_path=root/'build/kali/wireless-progress.json'
if wireless_path.exists():
    wireless=json.loads(wireless_path.read_text())
    if wireless.get('boot_version') in ('v15', 'v16'):
        version = wireless['boot_version']
        progress['booted_version'] = version + '; ' + wireless['kernel']
        progress['installed_image']='aura-kali-trial-' + version + '.img SHA256 '+wireless['boot']['sha256']
        progress['wireless_progress']=wireless
        progress['evidence'] += wireless['evidence']
        data['status']=data['status'].replace('NetHunter v14','NetHunter ' + version)+' MicroSD detection, read samples and read-only exFAT mount verified. ' + wireless['status']
torch_path = root/'build/kali/torch-progress.json'
if torch_path.exists():
    torch = json.loads(torch_path.read_text())
    if torch.get('installed'):
        progress['booted_version'] = 'v17; same #11 kernel as v16, CCI0 flashlight bus and regulator enabled.'
        progress['installed_image'] = 'aura-kali-trial-v17.img SHA256 ' + torch['boot']['sha256']
        progress['torch_progress'] = torch
        progress['verified']['torch_controller'] = torch['status']
        progress['evidence'] += torch['evidence']
        progress['blocked']['light_proximity'] += ' Exact factory path config was also tested on v16; sensors remained absent, previous configuration restored and accelerometer reverified.'
        data['status'] = data['status'].replace('NetHunter v16', 'NetHunter v17') + ' ' + torch['status']
        if wireless.get('validation', {}).get('user_confirmed_charging_icon'):
            progress['not_ported'] = [item for item in progress['not_ported'] if item != 'wireless charging integration']
            progress['verified']['wireless_charging'] = wireless['status']
            progress['blocked']['wireless_endurance'] = wireless['validation']['limitations']
camera_path = root/'build/kali/camera-progress.json'
if camera_path.exists():
    camera = json.loads(camera_path.read_text())
    if camera.get('installed'):
        progress['booted_version'] = 'v18; same #11 kernel, main rear IMX363 and CAMSS enabled.'
        progress['installed_image'] = 'aura-kali-trial-v18.img SHA256 ' + camera['boot']['sha256']
        progress['camera_progress'] = camera
        progress['verified']['rear_camera_capture'] = camera['status']
        progress['blocked']['camera_completion'] = camera['limitations']
        progress['evidence'] += camera['evidence']
        data['status'] = data['status'].replace('NetHunter v17', 'NetHunter v18') + ' ' + camera['status']
wifi_access_path = root/'build/kali/wifi-access.json'
if wifi_access_path.exists():
    wifi_access = json.loads(wifi_access_path.read_text())
    if wifi_access.get('installed'):
        progress['wifi_debugging'] = wifi_access
        progress['verified']['wifi_debugging'] = wifi_access['status']
        progress['evidence'] += wifi_access['evidence']
        data['status'] += ' User-approved persistent key-only Wi-Fi debugging enabled on the selected network; USB access retained.'
path.write_text(json.dumps(data,indent=2)+'\n')
