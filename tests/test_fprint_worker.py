"""Routing/process tests using synthetic state and a non-biometric executable."""
import os
import pwd
from pathlib import Path
import shutil
import signal
import time
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'port/aura-fingerprint'))
from aura_fprint_store import Store, StoreError
from aura_fprint_worker import AccountWorker, NativeRunner, PromptNativeRunner, Result


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.path = tempfile.mkdtemp(prefix='aura-fprint-worker-test-', dir='/var/lib')
        self.root = Path(self.path)
        with Store(self.path) as s:
            for uid, username, finger in ((1000, 'alice', 1), (1001, 'bob', 2)):
                record = s.begin(uid, username, finger)
                fd = os.open(self.root / record['database'], os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(fd, b'synthetic only')
                os.close(fd)
                s.commit(record['database'])
            self.record = s.list(1001, 'bob')[0]

    def tearDown(self):
        shutil.rmtree(self.path)

    def script(self, body):
        p = self.root / 'mock-native'
        p.write_text('#!/usr/bin/python3\n' + body)
        p.chmod(0o700)
        return NativeRunner(str(p))

    def test_routes_only_requested_account_and_holds_lock(self):
        outer = self
        class Runner:
            def run(self, record, capture, cancelled, progress):
                outer.assertEqual(record, outer.record)
                outer.assertTrue(capture)
                with outer.assertRaises(BlockingIOError):
                    Store(outer.path)
                return Result('match')
        worker = AccountWorker(self.path, Runner())
        self.assertEqual(worker.verify(1001, 'bob', 2).status, 'match')
        self.assertEqual(worker.verify(1000, 'alice', 2).status, 'not-enrolled')
        with self.assertRaises(StoreError):
            worker.verify(1001, 'alice', 2)
        self.assertEqual(worker.verify(1001, 'bob', 2, lambda: True).status, 'cancelled')

    def test_native_arguments_and_confirmed_match(self):
        runner = self.script("import sys\nassert sys.argv[1:4] == ['--account-verify', '1001', '2']\nassert len(sys.argv[4]) == 32\nprint('MATCH: firmware identified the stored template.')\n")
        self.assertEqual(AccountWorker(self.path, runner).verify(1001, 'bob', 2).status, 'match')

    def test_exit_alone_or_message_alone_never_matches(self):
        for body in ('pass\n', "import sys\nprint('MATCH: firmware identified the stored template.')\nsys.exit(1)\n"):
            result = self.script(body).run(self.record, True, lambda: False, lambda _: None)
            self.assertEqual(result.status, 'error')

    def test_no_match_retry_and_cancel(self):
        for code, message, expected in ((3, 'NO_MATCH', 'no-match'), (5, '', 'retry'), (4, '', 'cancelled')):
            result = self.script(f'import sys\nprint({message!r})\nsys.exit({code})\n').run(self.record, True, lambda: False, lambda _: None)
            self.assertEqual(result.status, expected)

    def test_cancellation_reaps_child_and_releases_store(self):
        marker = self.root / 'terminated'
        runner = self.script(f"import signal,time\nfrom pathlib import Path\ndef stop(*args):\n Path({str(marker)!r}).write_text('cleaned')\n raise SystemExit(4)\nsignal.signal(signal.SIGTERM, stop)\nprint('FINGER_LIFTED: place your finger on the sensor.', flush=True)\ntime.sleep(60)\n")
        events = []
        result = AccountWorker(self.path, runner).verify(1001, 'bob', 2, lambda: bool(events), events.append)
        self.assertEqual(result.status, 'cancelled')
        self.assertEqual(marker.read_text(), 'cleaned')
        with Store(self.path) as store:
            self.assertEqual(store.list(1001, 'bob'), [self.record])

    def test_excess_output_fails_closed(self):
        runner = self.script("import sys\nsys.stdout.write('X'*100000)\nprint('MATCH: firmware identified the stored template.')\n")
        self.assertEqual(runner.run(self.record, True, lambda: False, lambda _: None).status, 'error')

    def test_reload_is_not_authentication(self):
        runner = self.script("print('DATABASE_RELOADED: one enrolled template.')\n")
        self.assertEqual(runner.run(self.record, False, lambda: False, lambda _: None).status, 'ready')
        self.assertEqual(runner.run(self.record, True, lambda: False, lambda _: None).status, 'error')

    def enrollment_runner(self, outcome='saved', reload='ready', cancel_after=None):
        outer = self
        class Runner:
            calls = []
            def enroll(self, record, credential_fd, cancelled, progress):
                self.calls.append('enroll')
                self.record = record
                with outer.assertRaises(BlockingIOError):
                    Store(outer.path)
                file = outer.root / record['database']
                fd = os.open(file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.write(fd, b'synthetic staged database')
                os.close(fd)
                if cancel_after == 'enroll':
                    progress('cancel')
                return Result(outcome)
            def run(self, record, capture, cancelled, progress):
                self.calls.append('reload')
                outer.assertEqual(record, self.record)
                outer.assertFalse(capture)
                with outer.assertRaises(BlockingIOError):
                    Store(outer.path)
                if cancel_after == 'reload':
                    progress('cancel')
                return Result(reload)
        return Runner()

    def test_enrollment_publishes_only_after_fresh_reload(self):
        runner = self.enrollment_runner()
        self.assertEqual(AccountWorker(self.path, runner).enrollment(1001, 'bob', 3, -1).status, 'enrolled')
        self.assertEqual(runner.calls, ['enroll', 'reload'])
        with Store(self.path) as store:
            self.assertEqual(len(store.list(1001, 'bob')), 2)
            self.assertIn(runner.record, store.list(1001, 'bob'))
            self.assertEqual(len(store.list(1000, 'alice')), 1)

    def test_enrollment_failure_removes_only_pending_database(self):
        for outcome, reload in (('error', 'ready'), ('cancelled', 'ready'), ('retry', 'ready'), ('saved', 'error')):
            runner = self.enrollment_runner(outcome, reload)
            result = AccountWorker(self.path, runner).enrollment(1001, 'bob', 3, -1)
            self.assertNotEqual(result.status, 'enrolled')
            self.assertFalse((self.root / runner.record['database']).exists())
            with Store(self.path) as store:
                self.assertEqual(store.list(1001, 'bob'), [self.record])
                self.assertIsNone(store.state['pending'])

    def test_cancel_between_enroll_reload_and_commit(self):
        for phase in ('enroll', 'reload'):
            events = []
            runner = self.enrollment_runner(cancel_after=phase)
            result = AccountWorker(self.path, runner).enrollment(1001, 'bob', 3, -1, lambda: bool(events), events.append)
            self.assertEqual(result.status, 'cancelled')
            self.assertEqual(runner.calls, ['enroll'] if phase == 'enroll' else ['enroll', 'reload'])
            self.assertFalse((self.root / runner.record['database']).exists())

    def test_existing_finger_and_wrong_account_never_start_enrollment(self):
        runner = self.enrollment_runner()
        for uid, username, finger in ((1001, 'bob', 2), (1001, 'alice', 3)):
            with self.assertRaises(StoreError):
                AccountWorker(self.path, runner).enrollment(uid, username, finger, -1)
        self.assertEqual(runner.calls, [])

    def test_native_enrollment_uses_pipe_and_requires_saved_marker(self):
        read_fd, write_fd = os.pipe()
        try:
            # Synthetic value only; no real account PIN enters this test.
            os.write(write_fd, b'2468\n')
            os.close(write_fd)
            write_fd = -1
            runner = self.script("import os,sys\nassert sys.argv[1:4] == ['--account-enroll','1001','2']\nassert os.read(0, 100) == b'2468\\n'\nprint('ENROLLMENT_SAVED: one private template; no image exported.')\n")
            self.assertEqual(runner.enroll(self.record, read_fd, lambda: False, lambda _: None).status, 'saved')
            runner = self.script("print('MATCH: firmware identified the stored template.')\n")
            self.assertEqual(runner.enroll(self.record, read_fd, lambda: False, lambda _: None).status, 'error')
            with (self.root / self.record['database']).open('rb') as file:
                with self.assertRaises(StoreError):
                    runner.enroll(self.record, file.fileno(), lambda: False, lambda _: None)
        finally:
            os.close(read_fd)
            if write_fd >= 0:
                os.close(write_fd)

    def test_exception_after_capture_recovers_pending_state(self):
        runner = self.enrollment_runner()
        with patch.object(runner, 'run', side_effect=OSError('injected reload failure')):
            with self.assertRaises(OSError):
                AccountWorker(self.path, runner).enrollment(1001, 'bob', 3, -1)
        self.assertFalse((self.root / runner.record['database']).exists())
        with Store(self.path) as store:
            self.assertEqual(store.list(1001, 'bob'), [self.record])

    def test_native_enrollment_cancel_reaps_before_pending_cleanup(self):
        runner = self.script("import signal,time,sys\nfrom pathlib import Path\nu,f,i=sys.argv[2:]\np=Path(__file__).parent/f'u{u}-f{f}-{i}.db'\np.touch(mode=0o600)\ndef stop(*args):\n assert p.exists()\n raise SystemExit(4)\nsignal.signal(signal.SIGTERM,stop)\nprint('FINGER_LIFTED: place your finger on the sensor.',flush=True)\ntime.sleep(60)\n")
        read_fd, write_fd = os.pipe()
        events = []
        try:
            result = AccountWorker(self.path, runner).enrollment(1001, 'bob', 3, read_fd, lambda: bool(events), events.append)
            self.assertEqual(result.status, 'cancelled')
            self.assertEqual(list(self.root.glob('u1001-f3-*.db')), [])
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def test_prompt_runs_as_account_and_pipe_reaches_native_only(self):
        account = pwd.getpwnam('nobody')
        self.assertGreaterEqual(account.pw_uid, 1000)
        with tempfile.TemporaryDirectory(prefix='aura-prompt-synthetic-', dir='/var/tmp') as directory:
            os.chmod(directory, 0o755)
            prompt = Path(directory) / 'prompt'
            prompt.write_text('#!/usr/bin/python3\nimport os,sys\n'
                              f'assert os.getuid() == os.geteuid() == {account.pw_uid}\n'
                              'assert os.getgroups() == []\n'
                              "assert sys.argv[1] == '--credential-fd'\n"
                              "os.write(int(sys.argv[2]), b'2468\\n')\n")
            prompt.chmod(0o755)
            native = self.script("import os,sys\nfrom pathlib import Path\n"
                                 "assert os.geteuid() == 0 and os.read(0, 100) == b'2468\\n'\n"
                                 "u,f,i=sys.argv[2:]\np=Path(__file__).parent/f'u{u}-f{f}-{i}.db'\n"
                                 "if sys.argv[1]=='--account-enroll':\n"
                                 " fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)\n os.write(fd,b'synthetic')\n os.close(fd)\n"
                                 " print('ENROLLMENT_SAVED: one private template; no image exported.')\n"
                                 "else:\n assert p.exists()\n print('DATABASE_RELOADED: one enrolled template.')\n")
            # Reload has no credential pipe; use its own simple branch.
            native_path = Path(native.executable)
            body = native_path.read_text().replace("assert os.geteuid() == 0 and os.read(0, 100) == b'2468\\n'",
                "assert os.geteuid() == 0\nif sys.argv[1]=='--account-enroll': assert os.read(0, 100) == b'2468\\n'")
            native_path.write_text(body)
            runner = PromptNativeRunner(native.executable, str(prompt))
            result = AccountWorker(self.path, runner).enrollment(account.pw_uid, account.pw_name, 3)
            self.assertEqual(result.status, 'enrolled')

    def test_prompt_cancel_and_failure_do_not_publish(self):
        account = pwd.getpwnam('nobody')
        with tempfile.TemporaryDirectory(prefix='aura-prompt-synthetic-', dir='/var/tmp') as directory:
            os.chmod(directory, 0o755)
            prompt = Path(directory) / 'prompt'
            native = self.script("import os,sys\nassert not os.read(0,100)\nsys.exit(1)\n")
            for code, expected in ((4, 'cancelled'), (1, 'error')):
                prompt.write_text(f'#!/usr/bin/python3\nraise SystemExit({code})\n')
                prompt.chmod(0o755)
                runner = PromptNativeRunner(native.executable, str(prompt))
                result = AccountWorker(self.path, runner).enrollment(account.pw_uid, account.pw_name, 3)
                self.assertEqual(result.status, expected)
                with Store(self.path) as store:
                    self.assertEqual(store.list(account.pw_uid, account.pw_name), [])
                    self.assertIsNone(store.state['pending'])

    def test_sandbox_session_bus_is_bound_to_target_uid(self):
        runner = PromptNativeRunner(sandbox_session_bus=True)
        self.assertEqual(runner.session_bus_address(1000), 'unix:path=/run/aura-fprint-session-bus/1000')
        self.assertEqual(runner.session_bus_address(1001), 'unix:path=/run/aura-fprint-session-bus/1001')
        self.assertEqual(PromptNativeRunner().session_bus_address(1000), 'unix:path=/run/user/1000/bus')

    def test_prompt_rejects_changed_account_name_before_launch(self):
        account = pwd.getpwnam('nobody')
        runner = PromptNativeRunner('/does/not/exist', '/does/not/exist')
        with self.assertRaises(StoreError):
            AccountWorker(self.path, runner).enrollment(account.pw_uid, 'wrongname', 3)

    def test_store_lock_outlives_broker_until_native_exits(self):
        marker = self.root / 'child-ready'
        finished = self.root / 'child-finished'
        runner = self.script(f"import time\nfrom pathlib import Path\nPath({str(marker)!r}).touch()\ntime.sleep(1.2)\nPath({str(finished)!r}).touch()\n")
        broker = os.fork()
        if broker == 0:
            try:
                AccountWorker(self.path, runner).verify(1001, 'bob', 2)
            finally:
                os._exit(0)
        try:
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(marker.exists())
            os.kill(broker, signal.SIGKILL)
            os.waitpid(broker, 0)
            broker = 0
            with self.assertRaises(BlockingIOError):
                Store(self.path)
            while time.monotonic() < deadline:
                try:
                    with Store(self.path) as store:
                        self.assertTrue(finished.exists())
                        self.assertEqual(store.list(1001, 'bob'), [self.record])
                    break
                except BlockingIOError:
                    time.sleep(0.01)
            else:
                self.fail('Native child did not release its inherited lock')
        finally:
            if broker:
                os.kill(broker, signal.SIGKILL)
                os.waitpid(broker, 0)

    def test_capture_metrics_do_not_change_no_match_decision(self):
        runner = self.script("print('Capture metrics: coverage=40 quality=70')\n"
                             "print('Verification identify status=2')\n"
                             "print('Verification retry: identify-quality')\n"
                             "print('Verification identify status=999999999999')\n"
                             "print('Verification retry: private data')\n"
                             "print('Capture metrics: coverage=999999999999 quality=7')\n"
                             "print('Capture metrics: private raw data')\n"
                             "print('NO_MATCH')\nraise SystemExit(3)\n")
        events = []
        result = runner.run(self.record, True, lambda: False, events.append)
        self.assertEqual(result.status, 'no-match')
        self.assertEqual(events, ['capture-coverage=40 quality=70', 'identify-status=2', 'capture-retry=identify-quality'])

    def test_sample_progress_is_bounded_and_contains_no_raw_output(self):
        runner = self.script("print('Enrollment sample 1: status=1 remaining=19')\n"
                             "print('Enrollment sample 2: status=6 remaining=19')\n"
                             "print('Enrollment sample 3: status=1 remaining=999')\n"
                             "print('Enrollment sample not-structured')\n"
                             "print('ENROLLMENT_SAVED: one private template; no image exported.')\n")
        read_fd, write_fd = os.pipe()
        events = []
        try:
            self.assertEqual(runner.enroll(self.record, read_fd, lambda: False, events.append).status, 'saved')
            self.assertEqual(events, ['sample-status=1 remaining=19', 'sample-status=6 remaining=19'])
        finally:
            os.close(read_fd)
            os.close(write_fd)


if __name__ == '__main__':
    unittest.main(verbosity=2)
