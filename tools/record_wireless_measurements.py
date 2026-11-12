"""Summarize measured Qi telemetry without implying complete charging support."""
import json
import statistics
from pathlib import Path

root = Path(__file__).resolve().parents[1]
evidence = 'test-runs/kali-trial-v15/wireless-readonly-extended-result.txt'
text = (root / evidence).read_text()
text = text.rsplit('Recording restarted:', 1)[-1]
rows = [json.loads(line) for line in text.splitlines() if line.startswith('{')]
qi = [r for r in rows if r.get('chip_id') == '0x9220' and r.get('usb_online') == '0']
assert len(qi) >= 10
off = [r for r in rows if r['monotonic'] > qi[-1]['monotonic'] and r.get('usb_online') == '0']
summary = {
    'samples': len(qi),
    'duration_seconds': round(qi[-1]['monotonic'] - qi[0]['monotonic'], 3),
    'chip_id': '0x9220',
    'firmware': [qi[0]['fw_major'], qi[0]['fw_minor']],
    'median_receiver_output_uv': statistics.median(r['vout_uv_stock_formula'] for r in qi),
    'battery_current_ua_range': [min(int(r['battery_current_now']) for r in qi), max(int(r['battery_current_now']) for r in qi)],
    'median_battery_current_ua': statistics.median(int(r['battery_current_now']) for r in qi),
    'positive_current_samples': sum(int(r['battery_current_now']) > 0 for r in qi),
    'battery_temperature_deci_c_range': [min(int(r['battery_temp']) for r in qi), max(int(r['battery_temp']) for r in qi)],
    'reported_battery_status': sorted({r['battery_status'] for r in qi}),
    'post_removal_usb_disconnected_current_ua': [int(r['battery_current_now']) for r in off],
    'interpretation': 'Receiver supplies approximately 9 V and median battery current is positive on-pad; initial transient samples include discharge. This kernel explicitly inverts PMIC current to positive for charging; negative readings after pad removal confirm discharge. USB-only charger status check misreports Discharging on Qi. Small charge current is consistent with battery near the existing conservative 4.2 V ceiling. No receiver, DC current, FOD, GPIO, thermal or voltage settings changed.',
    'limitations': 'Short read-only test. Charge completion, sustained charging, thermal regulation across temperatures and Qi reporting after correction require further validation.',
    'evidence': evidence,
}
(root/'build/kali/wireless-measurements.json').write_text(json.dumps(summary, indent=2)+'\n')
p = root/'build/kali/wireless-progress.json'
progress = json.loads(p.read_text())
progress['status'] = 'v15 booted; Qi receiver responds and provides about 9 V. Positive battery charge current measured on-pad, but USB-only status logic reports Discharging. v16 reporting-only correction compiled and packaged; not installed.'
progress['measurements'] = summary
progress['candidate'] = {
    'version': 'v16',
    'sha256': json.loads((root/'build/kali/boot-manifest-v16.json').read_text())['files']['aura-kali-trial-v16.img']['sha256'],
    'scope': 'Razer-only read-only DC input supply and actual USB/DC charger status. Freezable polling notifies battery status changes. No changes to receiver settings or existing charging limit writes.',
    'status': 'Compiled, image roundtrip verified; USB disconnected before transfer. Not installed.',
}
if evidence not in progress['evidence']:
    progress['evidence'].append(evidence)
p.write_text(json.dumps(progress, indent=2)+'\n')
print(json.dumps(summary, indent=2))
