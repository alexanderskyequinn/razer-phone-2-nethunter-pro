from pathlib import Path
import json
import hashlib
root=Path(__file__).resolve().parents[1]
evidence=(root/'test-runs/kali-trial-v18/wifi-access-verify.txt').read_text()
assert 'Nonmatching Wi-Fi profile removes Wi-Fi listener and preserves USB.' in evidence
assert 'PasswordAuthentication no' in evidence and 'KbdInteractiveAuthentication no' in evidence
data={
    'installed':True,
    'install_id':'REPLACE_WITH_YOUR_INSTALL_ID',
    'profile_uuid':'2f461487-e000-4603-ad04-089b336de0c1',
    'last_address':'192.0.2.78',
    'port':22,
    'archive_sha256':hashlib.sha256((root/'build/kali/wifi-access.tar').read_bytes()).hexdigest(),
    'authorization':'User explicitly approved persistent key-only Wi-Fi debugging on the current network.',
    'status':'Existing trusted SSH host/client keys verified over Wi-Fi. Profile-scoped listener installed and enabled with NetworkManager reconnect hook. Nonmatching-profile removal and matching-profile restoration tested; USB retained. Temporary port2222 listener stopped.',
    'limitations':'Full reboot and physical Wi-Fi disconnect/reconnect not performed in this camera session. Listener uses current private IPv4 address only on the selected profile.',
    'remove':'Disable aura-wifi-ssh.service, remove /etc/aura-wifi-ssh-profile and /run/aura-wifi-ssh.conf, then reload ssh; the remaining hook is inactive without the profile file.',
    'evidence':['test-runs/kali-trial-v18/'+s for s in ['wifi-access-install.txt','wifi-port22-check.txt','wifi-access-verify.txt','camera-finish.txt']],
}
(root/'build/kali/wifi-access.json').write_text(json.dumps(data,indent=2)+'\n')
print(data['status'])
