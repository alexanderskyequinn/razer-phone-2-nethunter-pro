from pathlib import Path
import hashlib
import tarfile
root=Path(__file__).resolve().parents[1]
files={
    'usr/local/sbin/aura-wifi-ssh':0o755,
    'etc/NetworkManager/dispatcher.d/80-aura-wifi-ssh':0o755,
    'etc/ssh/sshd_config.d/20-aura-wifi.conf':0o644,
    'etc/systemd/system/aura-wifi-ssh.service':0o644,
}
archive=root/'build/kali/wifi-access.tar'
with tarfile.open(archive,'w') as package:
    for name,mode in files.items():
        source=root/'port/kali-overlay'/name
        info=package.gettarinfo(str(source),arcname=name)
        info.uid=info.gid=0
        info.uname=info.gname='root'
        info.mode=mode
        with source.open('rb') as stream:
            package.addfile(info,stream)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
script=f'''set -eu
test "$(cat /etc/aura-install-id)" = 'REPLACE_WITH_YOUR_INSTALL_ID'
test "$(nmcli -g GENERAL.CON-UUID device show wlan0)" = '2f461487-e000-4603-ad04-089b336de0c1'
echo '{digest}  /var/lib/aura/wifi-access.tar' | sha256sum -c -
test ! -e /etc/aura-wifi-ssh-profile
tar -xf /var/lib/aura/wifi-access.tar -C /
printf '%s\\n' '2f461487-e000-4603-ad04-089b336de0c1' > /etc/aura-wifi-ssh-profile
chmod 600 /etc/aura-wifi-ssh-profile
/usr/sbin/sshd -t
systemctl daemon-reload
systemctl enable --now aura-wifi-ssh.service
ss -lntp '( sport = :22 )'
/usr/sbin/sshd -T | grep -iE '^(listenaddress|passwordauthentication|kbdinteractiveauthentication|permitrootlogin|pubkeyauthentication) '
'''
(root/'diagnostic/kali-wifi-access-install.sh').write_bytes(script.encode())
print(digest)
