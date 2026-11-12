"""Archive tested modules and userspace configuration without private firmware."""
import hashlib
import json
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
stage = root / 'build/kali/peripheral-modules'
expected = {
    'drivers/bluetooth/hci_uart.ko.zst': '536a0f953af925017769608ec53f071b85786645b8196d84d3037dfa1adc2172',
    'drivers/bluetooth/btqca.ko.zst': '99260f47d428730e732746519c913e82d45ace455a02ad388172228e144e3935',
    'sound/soc/qcom/snd-soc-sdm845.ko.zst': '1b113c7c2add49491d84f559c73f24066dd816b8062f59536922bce3897810f9',
}
files = {}
for relative, digest in expected.items():
    path = stage / relative
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, relative
    files['lib/modules/6.18.2-aura-bringup1+/kernel/' + relative] = path
overlay = root / 'port/kali-overlay'
for directory in ('usr/share/alsa/ucm2', 'usr/share/qcom/sdm845/Razer/aura/socinfo'):
    for path in sorted((overlay / directory).rglob('*')):
        if path.is_file():
            files[path.relative_to(overlay).as_posix()] = path
destination = root / 'build/kali/verified-audio-bluetooth-v10.tar'
with tarfile.open(destination, 'w') as archive:
    for name, path in files.items():
        info = archive.gettarinfo(str(path), arcname=name)
        info.mode = 0o644
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        with path.open('rb') as stream:
            archive.addfile(info, stream)
manifest = {
    'base_boot': 'aura-kali-trial-v10.img',
    'base_boot_sha256': 'eebf082561adab0bbe1a163cb2b34d71a04c96a325d120a7e4625c624eefe571',
    'kernel_release': '6.18.2-aura-bringup1+',
    'kernel_revision': 'a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0',
    'patch': 'port/razer-radio-audio-compatibility.patch',
    'verification': 'Bluetooth pairing and clear speaker tone user-confirmed. Microphone acoustic capture measured. Kernel modules survive full reboot. UCM routes corrected after reboot; desktop endpoints, silent playback and recording pass from disabled mixer state. Corrected UCM not yet tested through another full reboot. Sensor metadata did not fix light/proximity.',
    'ucm_reference': 'https://github.com/alsa-project/alsa-ucm-conf/blob/master/ucm2/Qualcomm/sdm845/HiFi-MM1.conf',
    'limitations': 'Not a standalone flashable image. Requires existing persistent Kali installation and previously extracted private firmware. Bluetooth sleep disabled; power management unvalidated.',
    'files': {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()},
    'archive_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
}
destination.with_suffix('.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(destination)
