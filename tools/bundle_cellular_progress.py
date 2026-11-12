"""Preserve device-specific cellular evidence separately from generic kernel fixes."""
import hashlib
import json
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
resolver = root / 'port/kali-overlay/etc/NetworkManager/conf.d/91-aura-resolver.conf'
binary = root / 'build/kali/cellular/aura-modem-data-mode'
digest = '9abbc20e73681cd1ee6dcc8e7b08eda5d92f2db60269c18def15669cd815e227'
assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest
files = [
    (binary, 'usr/local/libexec/aura-modem-data-mode', 0o755),
    (root / 'port/kali-overlay/etc/systemd/system/aura-modem-data-mode.service', 'etc/systemd/system/aura-modem-data-mode.service', 0o644),
    (root / 'port/kali-overlay/usr/local/sbin/aura-modem-data-startup', 'usr/local/sbin/aura-modem-data-startup', 0o755),
    (resolver, 'etc/NetworkManager/conf.d/91-aura-resolver.conf', 0o644),
    (root / 'port/aura-modem-data-mode.c', 'source/aura-modem-data-mode.c', 0o644),
]
archive_path = root / 'build/kali/cellular-startup-fix.tar'
with tarfile.open(archive_path, 'w') as archive:
    for source, destination, mode in files:
        info = archive.gettarinfo(str(source), arcname=destination)
        info.uid = info.gid = 0
        info.uname = info.gname = 'root'
        info.mode = mode
        with source.open('rb') as stream:
            archive.addfile(info, stream)
manifest = {
    'archive_sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest(),
    'helper_sha256': digest,
    'carrier': 'Verizon, active SIM supplied by user',
    'sim': 'Hot insertion produced anomalous QMI card state 0x4e despite ready USIM. Standard slot-1 SIM power off/on restored present/ready without PIN attempts or SIM data edits.',
    'data': 'Verizon LTE home registration and IPv4v6 vzwinternet bearer. Interface-bound HTTPS HTTP/2 200; subsequent Wi-Fi-off DNS/HTTPS also HTTP/2 200 after data-centric correction.',
    'selection': 'Initial gsm/umts/lte, automatic selection, cs-ps and voice-centric. mmcli EPS ps-2 reported verification failure but independent QMI readback confirms ps-only/data-centric. Low-power/online radio refresh then established working data. No band-mask or identity changes.',
    'resolver': {'path': str(resolver.relative_to(root)), 'sha256': hashlib.sha256(resolver.read_bytes()).hexdigest(), 'behavior': 'dns=default, rc-manager=symlink; existing /etc/resolv.conf link to /run/NetworkManager/resolv.conf retained. Fixes failing external resolvconf management. Included in overlay and existing build root.'},
    'profile': {'id': 'Verizon Internet', 'apn': 'vzwinternet', 'ip_type': 'ipv4v6', 'metered': True, 'home_only': True, 'autoconnect': True, 'route_metric': 700},
    'validation': 'User confirms browsing with Wi-Fi off. Seven cellular HTTPS checks passed over 183 seconds with continuous Verizon home registration. Final boot e7060155-1d1b-422b-a45a-f1deb80710f3 verifies SIM present/ready, successful startup service after modem initialization, data-centric/packet-only preferences, automatic Verizon Internet connection and HTTP/2 200 via qmapmux0.0 with Wi-Fi off. SSH remains USB-only; Phosh and CPU boost active. Long-term endurance not established.',
    'limitations': ['IMS status queries return InvalidOperation; voice and SMS not established.', 'No outgoing calls or messages sent.', 'Do not describe short tests as long-term reliability.', 'User post-reboot rotation accepted, with some sluggishness remaining.'],
    'access': 'SSH remains bound only to USB 192.0.2.1:22.',
    'evidence': ['sim-protocol.txt', 'sim-power-refresh.txt', 'sim-ready-status.txt', 'verizon-cellular-https.txt', 'cellular-drop-events.txt', 'cellular-data-mode.txt', 'cellular-mode-result.txt', 'cellular-radio-refresh.txt', 'cellular-only-verified.txt', 'cellular-persist-reboot.txt', 'data-mode-after-sim-installed.txt', 'cellular-final-reboot-verified.txt'],
    'evidence_directory': 'test-runs/kali-trial-v12',
    'references': ['https://www.verizon.com/support/knowledge-base-225007/', 'https://www.networkmanager.dev/docs/api/latest/NetworkManager.conf.html', 'https://raw.githubusercontent.com/linux-mobile-broadband/libqmi/main/data/qmi-service-nas.json'],
    'installation': 'Requires libqmi-glib5, libqrtr-glib0, Python 3 and ModemManager. Install archive runtime files, enable aura-modem-data-mode.service (WantedBy/PartOf ModemManager.service, ordered After) and reboot. Wrapper waits for enabled/searching/registered/connecting/connected state, then helper applies volatile data preferences with readback. Unavailable/locked SIM is skipped; restart service after SIM setup. Local image recipe and build root include helper and modem packages; no full rootfs image rebuilt. Carrier-specific connection lives on phone and is not baked into the generic image.',
    'rollback': 'Disable aura-modem-data-mode.service and reboot to restore stock volatile cs-ps/voice-centric usage. Delete only Verizon Internet to remove its APN profile. Remove 91-aura-resolver.conf and reload NetworkManager to restore resolver auto-selection.',
}
path = root / 'build/kali/cellular-progress.json'
path.write_text(json.dumps(manifest, indent=2) + '\n')
print(path)
