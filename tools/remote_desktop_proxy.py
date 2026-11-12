"""Serve only the bundled noVNC client, forwarding to the local SSH tunnel."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'build/remote-desktop/python-libs'))
from websockify.websocketproxy import websockify_init

if __name__ == '__main__':
    sys.argv = ['websockify', '--web', str(root / 'build/remote-desktop/noVNC-1.6.0'),
                '127.0.0.1:6080', '127.0.0.1:5901']
    websockify_init()
