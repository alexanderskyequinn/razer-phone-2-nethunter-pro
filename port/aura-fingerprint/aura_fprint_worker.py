"""Internal root-only account fingerprint bridge; not a public auth service.

The caller supplies an already-authorized system account. No authorization or
login policy is exposed here. Existing engineering templates are not imported.
"""
from dataclasses import dataclass
from contextlib import contextmanager, nullcontext
import os
import pwd
import re
import selectors
import stat
import subprocess
import time

from aura_fprint_store import NAME, Store, StoreError

STORE = '/var/lib/aura/fpc-test-store/accounts'
BINARY = '/usr/local/libexec/aura-fpc-account-worker'


@dataclass(frozen=True)
class Result:
    status: str
    stage: str = ''
    record_id: str = ''


class NativeRunner:
    def __init__(self, executable=BINARY):
        self.executable = executable
        self._store_lock_fd = None

    @contextmanager
    def hold_store_lock(self, fd):
        if self._store_lock_fd is not None:
            raise StoreError('Native runner already has an active transaction')
        self._store_lock_fd = fd
        try:
            yield
        finally:
            self._store_lock_fd = None

    def run(self, record, capture, cancelled, progress):
        return self._run(record, capture, cancelled, progress)

    def enroll(self, record, credential_fd, cancelled, progress):
        # Borrow a pipe read end, never read the credential into Python memory.
        if type(credential_fd) is not int or credential_fd < 0 or not stat.S_ISFIFO(os.fstat(credential_fd).st_mode):
            raise StoreError('A private credential pipe is required')
        return self._run(record, False, cancelled, progress, credential_fd)

    def _run(self, record, capture, cancelled, progress, credential_fd=None):
        Store._record(record)
        identity = NAME.fullmatch(record['database'])[3]
        enrolling = credential_fd is not None
        mode = '--account-enroll' if enrolling else '--account-verify' if capture else '--account-check'
        command = [self.executable, mode,
                   str(record['uid']), str(record['finger']), identity]
        if cancelled():
            return Result('cancelled')
        process = subprocess.Popen(command, stdin=credential_fd if enrolling else subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   cwd='/', env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C'},
                                   start_new_session=True, close_fds=True,
                                   pass_fds=() if self._store_lock_fd is None else (self._store_lock_fd,))
        output = bytearray()
        pending = bytearray()
        reason = None
        deadline = time.monotonic() + (320 if enrolling else 70 if capture else 20)
        terminated_at = None
        stage = 'starting'
        selector = selectors.DefaultSelector()
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            while True:
                now = time.monotonic()
                if reason is None:
                    if cancelled():
                        reason = 'cancelled'
                    elif now >= deadline:
                        reason = 'error'
                if reason is not None and terminated_at is None:
                    terminated_at = now
                    if process.poll() is None:
                        process.terminate()
                if terminated_at is not None and now - terminated_at >= 8 and process.poll() is None:
                    process.kill()
                for key, _ in selector.select(0.1):
                    chunk = os.read(key.fd, 4096)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if len(output) + len(chunk) > 65536:
                        reason = 'error'
                        continue
                    output.extend(chunk)
                    pending.extend(chunk)
                    while b'\n' in pending:
                        line, _, tail = pending.partition(b'\n')
                        pending = bytearray(tail)
                        if line == b'FINGER_LIFTED: place your finger on the sensor.' and reason is None:
                            progress('place-finger')
                        sample = re.fullmatch(rb'Enrollment sample ([0-9]{1,3}): status=([0-6]) remaining=([0-9]{1,3})', line)
                        if enrolling and sample and int(sample[3]) <= 100 and reason is None:
                            stage = f'sample-status={int(sample[2])} remaining={int(sample[3])}'
                            progress(stage)
                        metrics = re.fullmatch(rb'Capture metrics: coverage=([0-9]{1,10}) quality=([0-9]{1,10})', line)
                        if capture and metrics and reason is None and all(int(v) <= 0xffffffff for v in metrics.groups()):
                            progress(f'capture-coverage={int(metrics[1])} quality={int(metrics[2])}')
                        identify_status = re.fullmatch(rb'Verification identify status=([0-9]{1,10})', line)
                        if capture and identify_status and reason is None and int(identify_status[1]) <= 0x7fffffff:
                            progress(f'identify-status={int(identify_status[1])}')
                        if capture and reason is None and line in (b'Verification retry: capture', b'Verification retry: identify-quality'):
                            progress(line.decode().replace('Verification retry: ', 'capture-retry='))
                        for prefix, label in (
                            (b'AUTHORIZATION_ACCEPTED:', 'authorized'),
                            (b'Finish enrollment:', 'finishing'),
                            (b'Save private template database:', 'saving'),
                            (b'Load private template database:', 'reloading'),
                            (b'Select saved Linux fingerprint group:', 'selecting-group'),
                            (b'Validate single enrolled template:', 'checking-template'),
                        ):
                            if line.startswith(prefix):
                                stage = label
                if process.poll() is not None and (reason is not None or not selector.get_map()):
                    break
            code = process.wait()
            if reason is not None:
                return Result(reason, stage)
            lines = output.splitlines()
            if code == 4:
                return Result('cancelled')
            if code == 5:
                return Result('retry')
            if code == 3 and capture and b'NO_MATCH' in lines:
                return Result('no-match')
            success = (b'ENROLLMENT_SAVED: one private template; no image exported.' if enrolling else
                       b'MATCH: firmware identified the stored template.' if capture else b'DATABASE_RELOADED: one enrolled template.')
            if code == 0 and success in lines:
                return Result('saved' if enrolling else 'match' if capture else 'ready')
            return Result('error', stage)
        finally:
            selector.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            process.stdout.close()


class AccountWorker:
    def __init__(self, store_path=STORE, runner=None):
        self.store_path = store_path
        self.runner = runner if runner is not None else NativeRunner()

    def _guard(self, store):
        # The native child inherits the store lock. If the broker dies first,
        # recovery cannot unlink pending files until hardware cleanup exits.
        return self.runner.hold_store_lock(store.lock) if hasattr(self.runner, 'hold_store_lock') else nullcontext()

    def verify(self, uid, username, finger, cancelled=lambda: False, progress=lambda _: None, record_id=None):
        if os.geteuid():
            raise PermissionError('A trusted authorized root caller is required')
        Store._finger(finger)
        if cancelled():
            return Result('cancelled')
        # Held across the complete native operation, including process reaping.
        # Native code independently holds the shared legacy-app sensor lock.
        with Store(self.store_path) as store:
            records = [r for r in store.list(uid, username) if r['finger'] == finger]
            if not records:
                return Result('not-enrolled')
            if record_id is not None and NAME.fullmatch(records[0]['database'])[3] != record_id:
                return Result('not-enrolled')
            with self._guard(store):
                return self.runner.run(records[0], True, cancelled, progress)

    def enrollment(self, uid, username, finger, credential_fd=None, cancelled=lambda: False, progress=lambda _: None):
        """Stage, authorize/capture, close, reopen/validate, then publish.

        A trusted caller must authorize the account and supply the existing
        firmware credential through a prompt-owned pipe. This method never
        provisions or resets Gatekeeper, and does not collect a password.
        """
        if os.geteuid():
            raise PermissionError('A trusted authorized root caller is required')
        if cancelled():
            return Result('cancelled')
        with Store(self.store_path) as store:
            record = store.begin(uid, username, finger)
            committed = False
            try:
                with self._guard(store):
                    result = self.runner.enroll(record, credential_fd, cancelled, progress)
                if result.status != 'saved':
                    return result
                if cancelled():
                    return Result('cancelled')
                # Separate native process: firmware must reopen the saved DB.
                with self._guard(store):
                    result = self.runner.run(record, False, cancelled, progress)
                if result.status != 'ready':
                    return result if result.status in ('cancelled', 'retry') else Result('error')
                if cancelled():
                    return Result('cancelled')
                store.commit(record['database'])
                committed = True
                return Result('enrolled', record_id=NAME.fullmatch(record['database'])[3])
            finally:
                # NativeRunner returns/raises only after its child is reaped.
                # After manifest I/O failure, reopen performs crash recovery.
                if not committed and store.state is not None:
                    store.cancel()


class PromptNativeRunner(NativeRunner):
    """Standard GNOME prompt in the authorized account's session, not as root.

    This is an internal mechanism, not a substitute for fprintd authorization.
    The prompt explicitly requests the existing separate firmware setup PIN.
    A future credential migration must handle password changes before claiming
    this is the normal account-password enrollment experience.
    """
    def __init__(self, executable=BINARY, prompt='/usr/local/libexec/aura-fprint-prompt', *, sandbox_session_bus=False):
        super().__init__(executable)
        self.prompt = prompt
        self.sandbox_session_bus = sandbox_session_bus

    def session_bus_address(self, uid):
        # The service binds just this account's session-bus socket outside
        # ProtectHome's hidden /run/user tree. Never share a fixed user's bus.
        path = f'/run/aura-fprint-session-bus/{uid}' if self.sandbox_session_bus else f'/run/user/{uid}/bus'
        return 'unix:path=' + path

    def enroll(self, record, credential_fd, cancelled, progress):
        Store._record(record)
        if credential_fd is not None:
            raise StoreError('Prompt enrollment does not accept an external credential')
        account = pwd.getpwuid(record['uid'])
        if account.pw_name != record['username']:
            raise StoreError('Desktop account identity changed')
        if os.geteuid():
            raise PermissionError('An authorized root broker is required')
        if cancelled():
            return Result('cancelled')
        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        prompt = None
        try:
            prompt = subprocess.Popen([self.prompt, '--credential-fd', str(write_fd)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                pass_fds=(write_fd,), close_fds=True, start_new_session=True,
                user=account.pw_uid, group=account.pw_gid, extra_groups=[], cwd='/',
                env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
                     'XDG_RUNTIME_DIR': f'/run/user/{account.pw_uid}',
                     'DBUS_SESSION_BUS_ADDRESS': self.session_bus_address(account.pw_uid)})
            os.close(write_fd)
            write_fd = -1
            result = super().enroll(record, read_fd, cancelled, progress)
            try:
                prompt_code = prompt.wait(timeout=5)
            except subprocess.TimeoutExpired:
                return Result('error')
            if result.status == 'saved':
                return result if prompt_code == 0 else Result('error')
            return Result('cancelled') if prompt_code == 4 or cancelled() else result
        finally:
            os.close(read_fd)
            if write_fd >= 0:
                os.close(write_fd)
            if prompt is not None and prompt.poll() is None:
                prompt.terminate()
                try:
                    prompt.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    prompt.kill()
                    prompt.wait()
