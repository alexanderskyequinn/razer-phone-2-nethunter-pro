"""Consolidate captured hardware results without communicating with the phone."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for version in ('v10', 'v11'):
    run = root / 'test-runs' / ('mainline-' + version)
    report = (run / 'http-status-4.txt').read_text()
    supplies = {}
    current = None
    for line in report.splitlines():
        if line.startswith('POWER_SUPPLY_NAME='):
            current = line.partition('=')[2]
            supplies[current] = {}
        if current and line.startswith('POWER_SUPPLY_'):
            key, _, value = line.removeprefix('POWER_SUPPLY_').partition('=')
            supplies[current][key] = value
    result = {
        'power_supplies': supplies,
        'network_http_responses': len(json.loads((run / 'network-test.json').read_text())['responses']),
        'charging_limit': 'USB SDP 500 mA; configured battery voltage ceiling 4.2 V and current ceiling 900 mA',
        'net_charging_verified': False,
        'current_interpretation': 'Positive battery current indicates net discharge despite charger status Charging',
        'visual_confirmation': 'Physical clear color bars confirmed in v8; no separate user confirmation recorded for this version',
        'power_management': 'Normal unused clocks/domains/regulators handling' if version == 'v11' else 'Ignore-unused bring-up flags retained',
        'evidence': 'http-status-4.txt and network-test.json',
    }
    (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')

path = root / 'port-status.json'
status = json.loads(path.read_text())
status['status'] = 'Native display v8 visually verified; touch, USB networking, read-only UFS and battery reporting verified. Kali filesystem and desktop integration in progress.'
status['next_milestones'] = ['Complete Kali/Phosh filesystem and boot packaging', 'Validate graphical touchscreen session', 'Port Wi-Fi, GPU acceleration and remaining peripherals', 'Validate sustained charging and power management']
status['verified_on_phone']['display'] = status['verified_on_phone']['native_display']
status['verified_on_phone']['battery'] = 'Android A charging at 56%, 29 C during Kali build; native fuel gauge works, net charging not established on 500 mA PC USB input.'
status['mainline_bringup'].update(
    scope='Native PID1, USB network, UFS, RMI4 touch, dual-DSI DSC display, fuel gauge and bounded charger trial',
    state='v8 clear color bars; v11 normal power-management test retains USB and pattern-write operation',
    current_phone_state='Android A charging; experimental v11 boot_b and blank dtbo_b retained. userdata has not been erased.',
    result='test-runs/mainline-v11/result.json',
    evidence='test-runs/mainline-v8 through mainline-v11',
)
status['fastboot_troubleshooting']['pending'] = 'Native Kali image build'
status['firmware_backup'] = 'device-data/native-prerequisites/manifest.json; vendor firmware and private calibration preserved locally'
path.write_text(json.dumps(status, indent=2) + '\n')
