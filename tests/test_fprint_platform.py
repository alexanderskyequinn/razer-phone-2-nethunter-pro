"""Exercise real GUdev/libfprint discovery against isolated fake sysfs devices."""
import json,os,subprocess,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
binary='/var/tmp/aura-libfprint-platform/enumerate'
base='''P: /devices/platform/fingerprint
E: SUBSYSTEM=platform
E: DRIVER=aura-fpc-resources
E: OF_COMPATIBLE_N=1
E: OF_COMPATIBLE_0=razer,aura-fpc-resources
A: modalias=of:NfingerprintT(null)Crazer,aura-fpc-resources
L: driver=../../../bus/platform/drivers/aura-fpc-resources
'''
cases={
 'correct':(base,1),
 'wrong-compatible':(base.replace('razer,aura-fpc-resources','other,fingerprint'),0),
 'substring-rejected':(base.replace('razer,aura-fpc-resources','razer,aura-fpc-resources-extra'),0),
 'unbound':(base.replace('E: DRIVER=aura-fpc-resources\n','').replace('L: driver=../../../bus/platform/drivers/aura-fpc-resources\n',''),0),
 'wrong-driver':(base.replace('E: DRIVER=aura-fpc-resources','E: DRIVER=other').replace('drivers/aura-fpc-resources','drivers/other'),0),
 'missing-compatible-count':(base.replace('E: OF_COMPATIBLE_N=1\n',''),0),
 'oversized-compatible-count':(base.replace('OF_COMPATIBLE_N=1','OF_COMPATIBLE_N=999'),0),
 'second-compatible':(base.replace('OF_COMPATIBLE_N=1','OF_COMPATIBLE_N=2').replace('E: OF_COMPATIBLE_0=razer,aura-fpc-resources','E: OF_COMPATIBLE_0=generic,sensor\nE: OF_COMPATIBLE_1=razer,aura-fpc-resources'),1),
}
results={}
with tempfile.TemporaryDirectory(prefix='aura-fprint-test-') as folder:
 for name,(data,expected) in cases.items():
    p=Path(folder)/name;p.write_text(data+'\n')
    result=subprocess.run(['umockdev-run','--device',str(p),'--',binary],text=True,capture_output=True,timeout=15)
    assert result.returncode==0,(name,result.stdout,result.stderr)
    assert f'DEVICE_COUNT={expected}\n' in result.stdout,(name,result.stdout,result.stderr)
    if expected:
        assert 'FEATURES=0' in result.stdout and 'OPEN_REFUSED_AS_EXPECTED' in result.stdout,result.stdout
    results[name]='passed'
    print(name,': passed')
out=root/'build/kali/fingerprint/libfprint-platform-tests.json'
out.write_text(json.dumps(results,indent=2)+'\n')
