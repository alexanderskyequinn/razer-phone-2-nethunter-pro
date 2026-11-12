"""Read diagnostic HTTP reports during a bounded USB networking test."""
import argparse
import json
from pathlib import Path
import time
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version', choices=['v3', 'v4', 'v5', 'v6', 'v7', 'v8', 'v9', 'v10', 'v11'], required=True)
parser.add_argument('--seconds', type=int, default=105)
args = parser.parse_args()
assert 1 <= args.seconds <= 180
out = Path(__file__).resolve().parents[1] / ('test-runs/mainline-' + args.version)
out.mkdir(parents=True, exist_ok=True)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
deadline = time.monotonic() + args.seconds
successes = []
last_errors = {}
while time.monotonic() < deadline:
    for address in ('192.0.2.1', '169.254.84.5'):
        try:
            with opener.open('http://' + address + '/status.txt', timeout=1) as response:
                data = response.read(2 * 1024 * 1024)
            assert data.startswith(('AURA_MAINLINE_DIAG_' + args.version.upper()).encode())
            record = {'address': address, 'bytes': len(data), 'time': time.time()}
            (out / ('http-status-' + str(len(successes)) + '.txt')).write_bytes(data)
            successes.append(record)
            print(json.dumps(record), flush=True)
            break
        except Exception as error:
            last_errors[address] = str(error)
    if len(successes) >= 5:
        break
    time.sleep(3)
result = {'responses': successes, 'last_errors': last_errors}
(out / 'network-test.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result), flush=True)
