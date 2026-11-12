"""Run a local shell script over USB or authorized Wi-Fi, verifying the same phone key."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SSH = ['C:/Windows/System32/OpenSSH/ssh.exe', '-i', 'device-data/kali-access/id_ed25519', '-o', 'UserKnownHostsFile=device-data/kali-access/known_hosts', '-o', 'HostKeyAlias=192.0.2.1', '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5']

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('script', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--timeout', type=int, default=45)
    p.add_argument('--host', default='192.0.2.1')
    p.add_argument('--port', type=int, default=22)
    p.add_argument('--bind', help='Optional local interface address for hosts with multiple LAN adapters')
    args = p.parse_args()
    import ipaddress
    ipaddress.ip_address(args.host)
    if not 1 <= args.port <= 65535:
        p.error('port must be between 1 and 65535')
    command = SSH + ['-p', str(args.port), 'root@' + args.host]
    if args.bind:
        ipaddress.ip_address(args.bind)
        command = SSH + ['-b', args.bind, '-p', str(args.port), 'root@' + args.host]
    try:
        result = subprocess.run(command + ['sh -s'], input=args.script.read_bytes().replace(b'\r\n', b'\n'), cwd=ROOT, capture_output=True, timeout=args.timeout)
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(command, 124, exc.stdout or b'', (exc.stderr or b'') + b'\nSSH timed out; remote actions may still be running.\n')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(result.stdout + result.stderr)
        print(f'Saved SSH result to {args.output} (exit {result.returncode}).')
    else:
        print((result.stdout + result.stderr).decode(errors='replace'))
    raise SystemExit(result.returncode)
