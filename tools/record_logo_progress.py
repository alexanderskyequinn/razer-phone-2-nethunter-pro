"""Record logo controller bring-up separately from physical observation."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'build/kali'
health=(root/'test-runs/kali-trial-v14/first-boot-health.txt').read_text()
assert 'lp5523 Programmable led chip found' in health
assert all(f'aura:logo{i} brightness=0' in health for i in range(9))
p=out/'logo-progress.json'
d=json.loads(p.read_text())
d.update(status='v14 installed and booted; controller and nine channels initialize, current cap80 (8mA), brightness zero. User confirms three consistent blueish-white pulses. All nine channel colors user-verified; RGB control installed and readback tested.',boot_version='v14',boot_id='5becfb55-8b16-4b6c-ab4d-caa4df5093a4',rollback='/var/lib/aura/boot-v12-before-logo.img',evidence=['test-runs/kali-trial-v13/logo-modules-install.txt','test-runs/kali-trial-v13/logo-probe.txt','test-runs/kali-trial-v14/first-boot-health.txt'],build_root='Two LED modules installed in local image build root and future rootfs recipe. No full rootfs image regenerated.',configuration_fix='v13 lacked mandatory child color property; v14 adds it and uses driver-supported chan-name. DT color identifiers remain generic; userspace RGB mapping individually verified.',nfc='The v12 cached DTB omitted the previously ported NFC nodes. v14 restores their source definition; tag detection has not been repeated after this update.')
d['evidence'] += ['test-runs/kali-trial-v14/logo-light-result.txt','test-runs/kali-trial-v14/logo-light-result-repeat.txt']
d['evidence'] += ['test-runs/kali-trial-v14/logo-color-result.txt']
d['evidence'] += ['test-runs/kali-trial-v14/logo-individual-0-result.txt']
d['evidence'] += ['test-runs/kali-trial-v14/logo-individual-3-result.txt']
d['evidence'] += ['test-runs/kali-trial-v14/logo-individual-6-result.txt']
d.setdefault('individual_channel_observations', {}).update({'6':{'color':'red','location':'top left','basis':'user visual report'},'7':{'color':'red','location':'bottom right','basis':'user visual report'},'8':{'color':'red','location':'top right','basis':'user visual report'}})
d.setdefault('individual_channel_observations', {}).update({'3':{'color':'blue','location':'bottom right','basis':'user visual report'},'4':{'color':'green','location':'top right','basis':'user visual report'},'5':{'color':'blue','location':'all over, strongest top right','basis':'user visual report; optical spread versus multiple physical LEDs not established'}})
d.setdefault('individual_channel_observations', {}).update({'0':{'color':'blue','location':'top left','basis':'user visual report'},'1':{'color':'green','location':'bottom right','basis':'user visual report'},'2':{'color':'green','location':'bottom right','basis':'User observed green bottom right on eight-second recheck. Same location reported for channel1; exact spatial assignment remains unresolved.'}})
d['group_color_observation'] = {'user_verbatim':'blue yellow, rainbow, purple green followed by green teal, blue teal, red','interpretation':'Both candidate three-channel groupings produce mixed colors; individual channel mapping needed. Do not infer a complete RGB map from these observations.'}
d['evidence'] += ['test-runs/kali-trial-v14/logo-individual-2-result.txt','test-runs/kali-trial-v14/logo-control-install.txt']
d['rgb_mapping'] = {'red':[6,7,8],'green':[1,2,4],'blue':[0,3,5]}
d['control'] = {'path':'/usr/local/sbin/aura-logo','source':'port/kali-overlay/usr/local/sbin/aura-logo','sha256':'5d7535c21fd6f395b9f2645d22054209276a06a9f814560fceecb4da36fbcece','installed':True,'default':'off at boot','validation':'RGB 17/29/43 readback correct on all nine channels; invalid 256 rejected; all channels off afterward. Same file installed in local build root.'}
d['limits'] = 'All nine colors observed. Green channels1/2 both reported bottom right; exact spatial mapping unresolved. Current8mA capped8mA; color balance, power draw and suspend with logo enabled not characterized.'
d['control']['sudo_lookup_fix'] = 'Installed /usr/sbin/aura-logo symlink to /usr/local/sbin/aura-logo because sudo secure_path excludes /usr/local/sbin. Exact sudo aura-logo help/off commands verified; privileges unchanged. Build root and recipes updated.'
d['evidence'] += ['test-runs/kali-trial-v14/logo-command-path-fix.txt']
app_path=out/'logo-app/manifest.json'
if app_path.exists():
    app=json.loads(app_path.read_text())
    d['desktop_app']=app
    d['control']['sha256']=app['files']['usr/local/sbin/aura-logo']
    d['control']['validation'] += ' Screen-aware rainbow/solid service subsequently installed; actual Phosh blank/wake, color replacement, invalid input and explicit off pass.'
    d['status'] += ' Logo Light app installed; user confirms Rainbow button works. Rainbow and solid screen-off/on behavior verified.'
    d['evidence'] += app.get('evidence',[])
p.write_text(json.dumps(d,indent=2)+'\n')
p=out/'boot-manifest-v14.json';d=json.loads(p.read_text());d['status']='Installed with identity, partition, old/new hashes and readback verified; booted. Nine LED channels initialize off; desktop, Bluetooth, accelerometer, CPU boost and suspend hook healthy. User confirms three consistent blueish-white logo pulses; all nine colors observed and RGB helper readback verified.';d['rollback']='/var/lib/aura/boot-v12-before-logo.img';d['evidence']=['test-runs/kali-trial-v14/first-boot-health.txt'];p.write_text(json.dumps(d,indent=2)+'\n');(out/'boot-manifest.json').write_text(p.read_text())
