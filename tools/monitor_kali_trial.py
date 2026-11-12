"""Wait for key-authenticated native Kali USB access and retain boot evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', choices=['v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11'], default='v6')
parser.add_argument('--label', default='')
args = parser.parse_args()
assert all(c.isalnum() or c == '-' for c in args.label)
RUN = ROOT / ('test-runs/kali-trial-' + args.version + ('-' + args.label if args.label else ''))
RUN.mkdir(parents=True, exist_ok=True)
SSH = ['C:/Windows/System32/OpenSSH/ssh.exe', '-i', 'device-data/kali-access/id_ed25519', '-o', 'UserKnownHostsFile=device-data/kali-access/known_hosts', '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=3', 'root@192.0.2.1']
end = time.monotonic() + 240
while time.monotonic() < end:
    result = subprocess.run(SSH + ['uname -a'], cwd=ROOT, capture_output=True, timeout=8)
    if result.returncode == 0:
        (RUN / 'ssh-first-contact.txt').write_bytes(result.stdout + result.stderr)
        print('Native Kali USB SSH is available.', flush=True)
        break
    (RUN / 'ssh-last-error.txt').write_bytes(result.stderr)
    time.sleep(3)
else:
    raise SystemExit('No authenticated SSH contact within four minutes; inspect phone and recovery state.')

script = r'''
printf '\n--- KERNEL ---\n'
uname -a
cat /proc/cmdline
printf '\n--- ROOT MOUNTS ---\n'
findmnt /
findmnt /run/lower
printf '\n--- BOOT SERVICES ---\n'
systemctl --no-pager --failed
systemctl --no-pager status phosh aura-usb-gadget aura-usb-dhcp aura-first-boot-guard ssh
printf '\n--- USER SESSIONS ---\n'
loginctl list-sessions --no-pager
ls -l /run/user/1000/wayland* /dev/dri /dev/input
printf '\n--- BATTERY ---\n'
cat /sys/class/power_supply/qcom-battery/uevent
cat /sys/class/power_supply/pmi8998-charger/uevent
printf '\n--- KERNEL LOG ---\n'
dmesg
printf '\n--- JOURNAL ---\n'
journalctl -b --no-pager -n 1800
'''
for index in range(3):
    result = subprocess.run(SSH + ['sh -s'], input=script.encode(), cwd=ROOT, capture_output=True, timeout=45)
    (RUN / f'kali-status-{index}.txt').write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit('SSH snapshot failed; inspect recorded status.')
    print(f'Captured native Kali boot snapshot {index + 1}.', flush=True)
    if index != 2:
        time.sleep(15)
(RUN / 'network-test.json').write_text(json.dumps({'authenticated_ssh': True, 'snapshots': 3, 'epoch': time.time()}, indent=2))
