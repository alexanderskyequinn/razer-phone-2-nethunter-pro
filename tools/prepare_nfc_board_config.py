"""Package the captured Razer RF configuration; no controller firmware image."""
import hashlib
import json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = root / 'device-data/native-prerequisites/nfc-stock-config'
assert hashlib.sha256((source/'libnfc-nxp.conf').read_bytes()).hexdigest() == 'cf69b6d8eb0374b3684f1f2b5a19a860cc8b636982d0f8e30f9001e0b757a1aa'
commands = json.loads((source/'command-blocks.json').read_text())
selected = [('NXP_ACT_PROP_EXTN', bytes.fromhex(commands['NXP_ACT_PROP_EXTN'])),
            ('XTAL_CLOCK_FROM_ANDROID_HAL', bytes.fromhex('20020501a0030108'))]
for name in ['NXP_NFC_PROFILE_EXTN', 'NXP_EXT_TVDD_CFG_2'] + ['NXP_RF_CONF_BLK_'+str(i) for i in range(1,7)] + ['NXP_CORE_RF_FIELD', 'NXP_CORE_CONF']:
    selected.append((name, bytes.fromhex(commands[name])))
selected.append(('SCREEN_ON_FROM_ANDROID_HAL', bytes.fromhex('2f150100')))
for name, data in selected:
    assert len(data) == data[2]+3, name
    assert data[:2] in (bytes.fromhex('2002'), bytes.fromhex('2f02'), bytes.fromhex('2f15')), name
    if data[0] == 0x20:
        pos = 4
        for _ in range(data[3]):
            if data[pos] == 0xa0:
                pos += 2
            else:
                pos += 1
            size = data[pos]
            pos += size + 1
        assert pos == len(data), name
out = root / 'build/kali/nfc-screen-state'
out.mkdir(exist_ok=True)
payload = b''.join(data for _,data in selected)
(out/'razer-aura-nci-config.bin').write_bytes(payload)
(out/'manifest.json').write_text(json.dumps({'source':'Captured vendor_a/etc/libnfc-nxp.conf', 'clock_reference':'https://android.googlesource.com/platform/hardware/nxp/nfc/+/pie-qpr1-release/halimpl/hal/phNxpNciHal.cc', 'commands':[name for name,_ in selected], 'bytes':len(payload), 'sha256':hashlib.sha256(payload).hexdigest(), 'scope':'Original board clock, transmitter supply, RF tuning and standard NCI parameters. No controller firmware download or secure-element provisioning.'}, indent=2)+'\n')
print((out/'manifest.json').read_text())
