"""Record confirmed first image installation without claiming a successful boot."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
run = root / 'test-runs/kali-trial-v1'
for operation in ('flash-native-boot-b', 'flash-blank-dtbo-b', 'flash-kali-userdata'):
    assert json.loads((run / (operation + '.json')).read_text())['code'] == 0
path = root / 'port-status.json'
status = json.loads(path.read_text())
status['status'] = 'Native Linux display verified; native Kali/Phosh/NetHunter image built, checked and flashed. First Kali boot pending recovery of unresponsive bootloader USB connection.'
status['mainline_bringup']['current_phone_state'] = 'Slot B selected; native Kali boot_b and blank dtbo_b installed. userdata now contains Kali. Do not boot Android A unless intentionally recovering Android. Bootloader USB stopped responding after successful flash; no Kali reboot command has been sent.'
status['kali_image'] = {
    'boot_manifest': 'build/kali/boot-manifest.json',
    'rootfs_manifest': 'build/kali/rootfs-manifest.json',
    'packages': 'build/kali/packages.txt',
    'installation_evidence': 'test-runs/kali-trial-v1/',
    'booted': False,
    'desktop': 'Phosh from Kali packages; mobian-phosh metapackage bypassed because phosh-core/phosh-full are unavailable in current configured repositories',
    'temporary_test_pin': 'REDACTED',
    'root_policy': 'First trial mounts ext4 userdata read-only with RAM overlay',
    'trial_limits': '10-minute systemd guard, 15-minute independent watchdog',
    'usb_access': '192.0.2.1, key-only SSH, local private key under device-data/kali-access',
    'limitations': ['No GPU acceleration', 'Wi-Fi not ported', 'Audio/modem/Bluetooth not validated', 'Sustained native charging not established']
}
status['fastboot_troubleshooting']['active_slot_after_tests'] = 'b'
status['fastboot_troubleshooting']['pending'] = 'Bootloader USB recovery, then first native Kali boot'
path.write_text(json.dumps(status, indent=2) + '\n')
print('Recorded successful installation and pending first boot.')
