from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'diagnostic/kali-telecamera-app-trial.sh').read_text()
s=s.replace('/opt/aura-camera-tele-test','/opt/aura-camera-telefocus-test').replace('80-aura-tele-trial','80-aura-telefocus-trial')
anchor='test -x /opt/aura-camera-telefocus-test/bin/cam'
s=s.replace(anchor,'''echo 'd655cf613482f5dd77b6eb3c4041809f1b9697f6227c9ee7c3b2902fecbd4680  /var/lib/aura/aura-libcamera-telefocus-trial.tar.gz' | sha256sum -c -
install -d /opt/aura-camera-telefocus-test
tar -xzf /var/lib/aura/aura-libcamera-telefocus-trial.tar.gz --strip-components=2 -C /opt/aura-camera-telefocus-test opt/aura-camera
test -x /opt/aura-camera-telefocus-test/bin/cam''')
(root/'diagnostic/kali-telefocus-app-trial.sh').write_bytes(s.encode())
