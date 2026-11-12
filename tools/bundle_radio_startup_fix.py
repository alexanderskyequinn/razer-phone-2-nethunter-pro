"""Bundle the tested modem and WLAN startup fixes for the matching aura kernel."""
import hashlib
import json
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = 'lib/modules/6.18.2-aura-bringup1+/kernel/'
files = [
    ('build/kali/modem-nv-fix/qcom_q6v5_mss.ko.zst', base+'drivers/remoteproc/qcom_q6v5_mss.ko.zst', 'c31cf4a2947cd38e479830ddb84cd1f566b2da07c4251537c0137ab0fcc40329'),
    ('build/kali/wifi-startup/ath10k_snoc.ko.zst', base+'drivers/net/wireless/ath/ath10k/ath10k_snoc.ko.zst', 'efcb5524756c15bc6b0cd35c6d1e95cb194789c295065184d70c7fb0db0f2526'),
]
output = root/'build/kali/radio-startup-fix.tar'
with tarfile.open(output, 'w') as archive:
    for source, destination, digest in files:
        path = root/source
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        info = archive.gettarinfo(str(path), arcname=destination)
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        info.mode = 0o644
        with path.open('rb') as stream:
            archive.addfile(info, stream)
manifest = {
    'kernel_revision': 'a49cccfa7c9c4c7eb0b44e7bca5bdb6783aed8c0',
    'stock_reference_revision': '3a6cba3be385c5368d316fca52ecd51cf734345f',
    'files': [{'path': destination, 'sha256': digest} for _, destination, digest in files],
    'archive_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
    'verification': 'Modem remains running with recovery enabled. Wi-Fi association and DNS/HTTPS verified. Verizon LTE data works with active SIM: user browsing, seven HTTPS checks over 183 seconds and automatic reconnection after reboot pass. Separate cellular-startup-fix applies volatile packet-only/data-centric preference after modem initialization and includes resolver configuration. IMS voice/SMS not established. No new kernel changes for cellular tests.',
    'changes': ['Grant HLOS and MSS_MSA RW access to reserved FIH NV buffer before MBA, matching original Razer loader; no NV contents or partitions modified.', 'Razer-only skip of HOST_CAP, matching stock ICNSS. Sending HOST_CAP with old firmware caused later MSA_INFO error 90.'],
    'evidence': ['test-runs/kali-trial-v11/modem-nv-health.txt', 'test-runs/kali-trial-v11/wifi-startup-first-boot.txt', 'test-runs/kali-trial-v11/wifi-first-scan.txt', 'test-runs/kali-trial-v11/modem-online.txt', 'test-runs/kali-trial-v12/wifi-dns-fixed.txt', 'test-runs/kali-trial-v12/sim-ready-status.txt', 'test-runs/kali-trial-v12/cellular-mode-result.txt', 'test-runs/kali-trial-v12/cellular-only-verified.txt'],
    'rollback': ['/var/lib/aura/qcom_q6v5_mss-v11-original.ko.zst', '/var/lib/aura/ath10k_snoc-v11-original.ko.zst'],
    'installation': 'Matching kernel only; depmod and reboot required. ModemManager 1.24.2-2+b1 and libqmi-utils 1.38.0-1+b1 installed separately. Original firmware and reserved-memory DT required.',
    'access': 'SSH remains key-only and bound exclusively to USB address 192.0.2.1:22.',
}
output.with_suffix('.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(output)
