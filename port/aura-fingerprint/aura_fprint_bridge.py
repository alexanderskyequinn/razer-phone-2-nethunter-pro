#!/usr/bin/python3
"""Root-only libfprint subprocess protocol. fprintd owns caller authorization.

Only opaque record references cross this protocol, never biometric templates
or credentials. This is not a public D-Bus service and is not setuid.
"""
import os
import pwd
import re
import resource
import signal
import sys
import syslog
from pathlib import Path

# Python is launched with -I; only this root-installed module directory is added.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aura_fprint_store import NAME, Store, StoreError
from aura_fprint_worker import AccountWorker, PromptNativeRunner, STORE


def identity(arguments, record=False):
    if len(arguments) != (4 if record else 3):
        raise StoreError('Invalid argument count')
    uid_text, username, finger_text = arguments[:3]
    if not re.fullmatch(r'[1-9][0-9]{0,9}', uid_text) or not re.fullmatch(r'[1-9]|10', finger_text):
        raise StoreError('Invalid numeric identity')
    uid, finger = int(uid_text), int(finger_text)
    Store._identity(uid, username)
    account = pwd.getpwuid(uid)
    if account.pw_name != username or pwd.getpwnam(username).pw_uid != uid:
        raise StoreError('Account identity mismatch')
    token = arguments[3] if record else None
    if record and not re.fullmatch(r'[0-9a-f]{32}', token):
        raise StoreError('Invalid record reference')
    return uid, username, finger, token


def dispatch(arguments, store_path=STORE, worker=None, cancelled=lambda: False, emit=print):
    if os.geteuid():
        raise PermissionError('Authorized root caller required')
    if not arguments:
        raise StoreError('Operation required')
    operation, *values = arguments
    worker = worker or AccountWorker(store_path, PromptNativeRunner(sandbox_session_bus=True))
    if operation in ('ready', 'list'):
        if values:
            raise StoreError('Unexpected arguments')
        with Store(store_path) as store:
            if operation == 'list':
                for item in store.state['records']:
                    # Do not attach a reassigned UID's old enrollment to its new owner.
                    try:
                        account = pwd.getpwuid(item['uid'])
                    except KeyError:
                        continue
                    if account.pw_name != item['username']:
                        continue
                    token = NAME.fullmatch(item['database'])[3]
                    emit(f"RECORD {item['uid']} {item['username']} {item['finger']} {token}")
        emit('RESULT ready' if operation == 'ready' else 'RESULT listed')
        return
    if operation not in ('enroll', 'verify', 'delete'):
        raise StoreError('Unknown operation')
    uid, username, finger, token = identity(values, operation != 'enroll')
    if cancelled():
        emit('RESULT cancelled')
        return
    def progress(event):
        if operation == 'verify' and re.fullmatch(r'capture-coverage=[0-9]{1,10} quality=[0-9]{1,10}|identify-status=[0-9]{1,10}|capture-retry=(?:capture|identify-quality)', event):
            syslog.syslog(syslog.LOG_INFO, 'AURA_FPRINT_CAPTURE ' + event)
            return
        if event == 'place-finger':
            emit('TOUCH')
        else:
            sample = re.fullmatch(r'sample-status=([0-6]) remaining=([0-9]{1,3})', event)
            if sample and int(sample[2]) <= 100:
                emit(f'SAMPLE {sample[1]} {sample[2]}')
    if operation == 'enroll':
        result = worker.enrollment(uid, username, finger, cancelled=cancelled, progress=progress)
        if result.status == 'enrolled':
            if not re.fullmatch(r'[0-9a-f]{32}', result.record_id):
                raise StoreError('Missing committed record reference')
            emit(f'RECORD {uid} {username} {finger} {result.record_id}')
    elif operation == 'verify':
        result = worker.verify(uid, username, finger, cancelled=cancelled, progress=progress, record_id=token)
    else:
        with Store(store_path) as store:
            records = [r for r in store.list(uid, username) if r['finger'] == finger]
            if not records or NAME.fullmatch(records[0]['database'])[3] != token:
                emit('RESULT not-enrolled')
                return
            store.delete(uid, username, finger)
        emit('RESULT deleted')
        return
    if result.status not in ('enrolled', 'match', 'no-match', 'not-enrolled', 'cancelled', 'retry', 'error'):
        raise StoreError('Unexpected worker result')
    emit('RESULT ' + result.status)


def main():
    if os.geteuid():
        return 1
    os.umask(0o077)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    cancelled = False
    def stop(*_):
        nonlocal cancelled
        cancelled = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        dispatch(sys.argv[1:], cancelled=lambda: cancelled, emit=lambda line: print(line, flush=True))
        return 0
    except BlockingIOError:
        print('RESULT retry', flush=True)
        return 0
    except (OSError, ValueError, KeyError, StoreError):
        # No exception text, usernames, paths or template bytes in error output.
        print('RESULT error', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
