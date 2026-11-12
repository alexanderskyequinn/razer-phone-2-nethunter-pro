"""Bounded LAN transfer test over the already-authorized SSH connection."""
from pathlib import Path
import argparse,json,subprocess,time
from kali_ssh import SSH,ROOT
parser=argparse.ArgumentParser()
parser.add_argument('--label',choices=['baseline','power-save-off','cubic','after-reboot'],default='baseline')
parser.add_argument('--mib',type=int,choices=[1,4,8],default=4)
options=parser.parse_args()
size=options.mib*1024*1024
base=SSH+['-o','Compression=no','root@192.0.2.78']
results={}
# Synthetic bytes only: no device files, network listener, or persistent change.
for direction,command,payload in [
 ('phone_to_pc',f'head -c {size} /dev/zero',None),
 ('pc_to_phone',f'python3 -c \'import sys; print(len(sys.stdin.buffer.read({size})))\'',b'\0'*size),
]:
    started=time.monotonic()
    try:
        result=subprocess.run(base+[command],input=payload,stdout=subprocess.DEVNULL if payload is None else subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT,timeout=50)
        elapsed=time.monotonic()-started
        assert result.returncode==0,result.stderr.decode(errors='replace')
        if payload is not None:assert result.stdout.strip()==str(size).encode(),result.stdout
        results[direction]={'bytes':size,'seconds':round(elapsed,3),'mbit_per_second':round(size*8/elapsed/1e6,2)}
        print(direction,results[direction],flush=True)
    except (subprocess.TimeoutExpired,AssertionError) as e:
        results[direction]={'error':str(e)};print(direction,'failed',flush=True)
out=ROOT/f'test-runs/snapshot/hardware-wifi-lan-{options.label}.json';out.write_text(json.dumps(results,indent=2)+'\n')
