"""Record measured attach/detach transitions and the user's charging-icon check."""
import json
import statistics
from pathlib import Path

root = Path(__file__).resolve().parents[1]
evidence = 'test-runs/kali-trial-v16/wireless-reporting-result.txt'
text = (root/evidence).read_text().rsplit('Recording restarted:', 1)[-1]
rows = [json.loads(line) for line in text.splitlines() if line.startswith('{')]
qi = [r for r in rows if r.get('wireless_online') == '1' and r.get('usb_online') == '0']
assert len(qi) >= 3
assert all(r['wireless_present'] == '1' for r in qi)
assert any(r['battery_status'] == 'Charging' and r['charger_status'] == 'Charging' for r in qi)
detached = [r for r in rows if r['monotonic'] > qi[-1]['monotonic'] and r.get('usb_online') == '0' and r.get('wireless_online') == '0']
assert detached and all(r['battery_status'] == 'Discharging' for r in detached)
usb = [r for r in rows if r['monotonic'] > detached[-1]['monotonic'] and r.get('usb_online') == '1']
assert usb and any(r['battery_status'] == 'Charging' for r in usb)
summary = {
    'qi_samples': len(qi),
    'observed_qi_seconds': round(qi[-1]['monotonic']-qi[0]['monotonic'], 3),
    'median_battery_current_ua': statistics.median(int(r['battery_current_now']) for r in qi),
    'battery_current_ua_samples': [int(r['battery_current_now']) for r in qi],
    'battery_status_sequence': [r['battery_status'] for r in qi],
    'charger_status_sequence': [r['charger_status'] for r in qi],
    'temperature_deci_c_range': [min(int(r['battery_temp']) for r in qi), max(int(r['battery_temp']) for r in qi)],
    'wireless_online_and_charging': True,
    'pad_removal_returns_to_discharging': True,
    'usb_reconnection_returns_to_charging': True,
    'user_confirmed_charging_icon': True,
    'limitations': 'Very brief functional test. Initial attach sample retains Discharging before the next poll updates it; some current samples show net discharge under load. Sustained net charging, full charge cycle, pad alignment, thermal control across temperatures and suspend-on-Qi remain unvalidated. Receiver configuration and charge limits were not changed.',
    'evidence': evidence,
}
(root/'build/kali/wireless-reporting-result.json').write_text(json.dumps(summary, indent=2)+'\n')
p = root/'build/kali/wireless-progress.json'
progress = json.loads(p.read_text())
assert progress['boot_version'] == 'v16'
progress['status'] = 'Basic Qi charging and correct desktop indication verified. Receiver output and positive median battery current measured; v16 reports wireless present/online and Charging without USB. Removing from pad reports Discharging; reconnecting USB reports Charging. User confirms charging icon. Sustained charging/thermal tests remain.'
progress['validation'] = summary
progress['candidate']['status'] = progress['status']
progress['evidence'] = list(dict.fromkeys(progress['evidence'] + [evidence]))
p.write_text(json.dumps(progress, indent=2)+'\n')
manifest_path = root/'build/kali/boot-manifest-v16.json'
manifest = json.loads(manifest_path.read_text())
manifest['status'] = 'Installed, readback verified and booted. Basic Qi charging indication and pad/USB transitions verified; user confirms icon. Sustained power/thermal tests remain.'
manifest['evidence'] = list(dict.fromkeys(manifest['evidence'] + [evidence]))
for path in (manifest_path, root/'build/kali/boot-manifest.json'):
    path.write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps(summary, indent=2))
