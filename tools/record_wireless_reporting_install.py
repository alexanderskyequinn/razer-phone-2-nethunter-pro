"""Record only verified installation and boot results; Qi UI validation is pending."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
evidence = 'test-runs/kali-trial-v16/first-boot-health.txt'
health = (root/evidence).read_text()
assert 'Verified v16 boot image installed to boot_b; v15 backup verified.' in health
assert 'POWER_SUPPLY_NAME=pmi8998-wireless' in health
assert 'POWER_SUPPLY_ONLINE=1' in health
assert '#11 SMP PREEMPT' in health
manifest_path = root/'build/kali/boot-manifest-v16.json'
manifest = json.loads(manifest_path.read_text())
manifest['status'] = 'Installed with verified v15 backup and readback. Booted #11; wireless supply registered, UPower recognizes it, USB charging and desktop services work. Qi status transition test pending.'
manifest['rollback'] = '/var/lib/aura/boot-v15-before-wireless-reporting.img'
manifest['evidence'] = [evidence, 'build/kali/wireless-reporting-review.json']
for path in (manifest_path, root/'build/kali/boot-manifest.json'):
    path.write_text(json.dumps(manifest, indent=2)+'\n')
p = root/'build/kali/wireless-progress.json'
progress = json.loads(p.read_text())
progress['status'] = 'Qi receiver identification, approximately 9 V output and small positive median battery current verified on v15. v16 reporting correction installed and booted; UPower recognizes wireless source. Qi status transition and visible charging icon validation pending.'
progress['boot_version'] = 'v16'
progress['boot'] = manifest['files']['aura-kali-trial-v16.img']
progress['boot_id'] = health.splitlines()[1]
progress['rollback'] = manifest['rollback']
progress['kernel'] = 'Linux #11, reporting-only PMI8998 DC input correction; unchanged v15 DTB and kernel configuration. Existing charging limits retained.'
progress['scope'] = 'Receiver I2C bus enabled and wireless power status exposed. No receiver register, GPIO enable, firmware, FOD, voltage or charge current setting changes for wireless bring-up.'
progress['candidate']['status'] = manifest['status']
progress['evidence'] = list(dict.fromkeys(progress['evidence'] + manifest['evidence']))
p.write_text(json.dumps(progress, indent=2)+'\n')
print(manifest['status'])
