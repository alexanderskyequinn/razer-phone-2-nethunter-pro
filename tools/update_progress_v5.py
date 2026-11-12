import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
run = root / 'test-runs/mainline-v5'
verified = json.loads((run / 'restoration-verification.json').read_text())
assert verified['slot'] == '_a'
assert all(x['matches_original'] for x in verified['partitions'].values())
result = json.loads((run / 'result.json').read_text())
result['restoration'] = 'Android slot A; all six original boot/dtbo/vbmeta hashes verified'
(run / 'result.json').write_text(json.dumps(result, indent=2))
path = root / 'port-status.json'
status = json.loads(path.read_text())
status['status'] = 'Native Linux 6.18.2, USB networking, read-only UFS access and touchscreen events verified. Android restored. Display driver under development; NetHunter Pro userspace not integrated.'
status['next_milestones'] = ['Bring up NT36830 dual-DSI display', 'Validate charging, battery reporting and thermal behavior', 'Integrate Kali userspace and NetHunter Pro packaging', 'Port Wi-Fi and remaining peripherals']
status['verified_on_phone'].update(battery='50%, charging, 30 C after v5 restoration', touch=result['touch'], storage=result['storage_reads_verified'], display='Active NT36830 external-clock dual-DSI command panel; live timing specifies DSC 10 bpc, 8 bpp and RGB888 input. Native display not yet working.')
status['fastboot_troubleshooting'].update(pending='Display test preparation', final_restoration='test-runs/mainline-v5/restoration-verification.json')
status['mainline_bringup'].update(scope='Native PID1, USB2 network/report disk, read-only UFS, Synaptics touchscreen. Experimental display driver in development.', state='v3 network, v4 storage and v5 touchscreen hardware tests passed', evidence='test-runs/mainline-v5/', restoration='test-runs/mainline-v5/restoration-verification.json', usb_network='DHCP assigned Windows 192.0.2.2; five HTTP status downloads passed in each of v3, v4 and v5.', result='test-runs/mainline-v5/result.json')
path.write_text(json.dumps(status, indent=2))
