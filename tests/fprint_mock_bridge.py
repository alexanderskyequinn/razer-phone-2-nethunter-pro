"""Synthetic child protocol only. Never installed on the phone."""
from pathlib import Path
import sys
import time

scenario = Path('/var/tmp/aura-libfprint-operations/scenario').read_text().strip()
operation, *args = sys.argv[1:]
record = 'RECORD 65534 nobody 2 0123456789abcdef0123456789abcdef'
if operation == 'ready':
    print('RESULT error' if scenario == 'open-error' else 'RESULT ready')
elif operation == 'list':
    if scenario == 'list-bad-id': print(record.replace('0123456789abcdef0123456789abcdef', '../bad'))
    elif scenario == 'list-wrong-account': print(record.replace('nobody', 'root'))
    else:
        print(record)
        if scenario == 'list-duplicate': print(record)
    print('RESULT listed')
elif operation == 'verify':
    assert args == ['65534', 'nobody', '2', '0123456789abcdef0123456789abcdef']
    if scenario == 'verify-match': print('RESULT match')
    elif scenario == 'verify-no-match': print('RESULT no-match')
    elif scenario == 'verify-stale': print('RESULT not-enrolled')
    elif scenario == 'verify-exit-fail': print('RESULT match'); sys.exit(1)
    elif scenario == 'verify-double': print('RESULT match\nRESULT match')
    elif scenario == 'verify-no-result': pass
    elif scenario == 'verify-truncated': sys.stdout.write('RESULT match')
    elif scenario == 'verify-flood': sys.stdout.write('X'*100000)
    elif scenario == 'verify-nul': sys.stdout.buffer.write(b'RESULT match\0\n')
    elif scenario == 'verify-cancel': time.sleep(60)
    else: raise AssertionError('Invalid metadata reached bridge')
elif operation == 'enroll':
    assert args == ['65534', 'nobody', '3']
    print('TOUCH\nSAMPLE 1 19\nSAMPLE 6 19\nSAMPLE 1 1\nSAMPLE 0 0')
    if scenario != 'enroll-no-record': print(record.replace('nobody 2', 'nobody 4' if scenario == 'enroll-wrong-finger' else 'nobody 3'))
    print('RESULT enrolled')
elif operation == 'delete':
    assert args == ['65534', 'nobody', '2', '0123456789abcdef0123456789abcdef']
    print('RESULT deleted')
else:
    raise AssertionError('Unknown operation')
