"""Record the verified torch boot and optionally the user's on/off check."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--user-verified', action='store_true')
parser.add_argument('--brightness-verified', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
evidence = 'test-runs/kali-trial-v17/first-boot-health-third.txt'
health = (root/evidence).read_text()
assert 'Verified v17 boot image installed to boot_b; v16 backup verified.' in health
assert '/16-0063' in health and 'TORCH\n0\n32' in health
assert '0 loaded units listed.' in health
p = root/'build/kali/torch-progress.json'
data = json.loads(p.read_text())
data['installed'] = True
data['boot_id'] = health.splitlines()[1]
data['user_on_off_verified'] = args.user_verified or data.get('user_on_off_verified', False)
data['user_brightness_verified'] = args.brightness_verified or data.get('user_brightness_verified', False)
data['status'] = 'v17 installed with verified v16 rollback and readback; boots original #11 kernel. LM3644 responds on CCI0 and registers aura:white:torch with32 levels. Desktop and sensors active; no failed units.'
data['status'] += (' User confirms Phosh flashlight button turns rear light on and off.' if data['user_on_off_verified'] else ' Physical Phosh flashlight button test pending.')
if data['user_brightness_verified']:
    data['status'] += ' User also confirms brightness adjustment works.'
data['limits'] = 'Conservative torch only, maximum under89mA per LED even on TT variant. Flash/strobe/camera synchronization unimplemented; sustained use and torch suspend behavior not physically verified.'
data['package'] = 'External module and source retained; local rootfs build root and module recipe updated. Full rootfs image not regenerated.'
data['evidence'] = [evidence]
p.write_text(json.dumps(data, indent=2)+'\n')
p = root/'build/kali/boot-manifest-v17.json'
manifest = json.loads(p.read_text())
manifest['status'] = data['status']
manifest['rollback'] = data['rollback']
manifest['evidence'] = data['evidence']
for dest in (p, root/'build/kali/boot-manifest.json'):
    dest.write_text(json.dumps(manifest, indent=2)+'\n')
print(data['status'])
