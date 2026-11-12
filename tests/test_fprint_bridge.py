"""Root-only bridge identity, stale-reference and protocol checks; synthetic DBs."""
import os
from pathlib import Path
import pwd
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'port/aura-fingerprint'))
from aura_fprint_store import NAME, Store, StoreError
from aura_fprint_worker import AccountWorker, Result
from aura_fprint_bridge import dispatch, identity


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.account = pwd.getpwnam('nobody')
        self.root = Path(tempfile.mkdtemp(prefix='aura-bridge-test-', dir='/var/lib'))
        with Store(str(self.root)) as store:
            self.record = store.begin(self.account.pw_uid, self.account.pw_name, 2)
            fd = os.open(self.root/self.record['database'], os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
            os.write(fd, b'synthetic'); os.close(fd)
            store.commit(self.record['database'])
        self.token = NAME.fullmatch(self.record['database'])[3]
        self.args = [str(self.account.pw_uid), self.account.pw_name, '2', self.token]

    def tearDown(self):
        shutil.rmtree(self.root)

    def call(self, args, **kwargs):
        output = []
        dispatch(args, str(self.root), emit=output.append, **kwargs)
        return output

    def test_ready_and_list_opaque_reference_only(self):
        self.assertEqual(self.call(['ready']), ['RESULT ready'])
        self.assertEqual(self.call(['list']), ['RECORD ' + ' '.join(self.args), 'RESULT listed'])

    def test_invalid_or_reassigned_identity_fails_before_worker(self):
        for values in (['0', 'root', '2', self.token], ['065534', 'nobody', '2', self.token],
                       [self.args[0], 'wrong', '2', self.token], [*self.args[:2], '11', self.token],
                       [*self.args[:3], '../private'], [*self.args, 'extra']):
            with self.assertRaises((StoreError, KeyError)):
                identity(values, True)

    def test_stale_reference_never_reaches_native_matching(self):
        class Runner:
            def run(self, *args):
                raise AssertionError('Stale reference reached hardware')
        worker = AccountWorker(str(self.root), Runner())
        self.assertEqual(self.call(['verify', *self.args[:3], '0'*32], worker=worker), ['RESULT not-enrolled'])

    def test_delete_is_bound_to_exact_reference(self):
        self.assertEqual(self.call(['delete', *self.args[:3], '0'*32]), ['RESULT not-enrolled'])
        self.assertTrue((self.root/self.record['database']).exists())
        self.assertEqual(self.call(['delete', *self.args]), ['RESULT deleted'])
        self.assertFalse((self.root/self.record['database']).exists())
        self.assertEqual(self.call(['list']), ['RESULT listed'])

    def test_recreated_finger_does_not_match_old_reference(self):
        self.call(['delete', *self.args])
        with Store(str(self.root)) as store:
            new = store.begin(self.account.pw_uid, self.account.pw_name, 2)
            fd = os.open(self.root/new['database'], os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0o600)
            os.write(fd, b'new synthetic'); os.close(fd); store.commit(new['database'])
        self.assertEqual(self.call(['verify', *self.args]), ['RESULT not-enrolled'])

    def test_cancel_does_not_delete(self):
        self.assertEqual(self.call(['delete', *self.args], cancelled=lambda: True), ['RESULT cancelled'])
        self.assertTrue((self.root/self.record['database']).exists())

    def test_nonroot_denied(self):
        with patch('os.geteuid', return_value=1000), self.assertRaises(PermissionError):
            self.call(['list'])

    def test_enrollment_success_requires_record_reference(self):
        class Worker:
            def enrollment(self, *args, **kwargs): return Result('enrolled')
        with self.assertRaises(StoreError):
            self.call(['enroll', *self.args[:3]], worker=Worker())

    def test_progress_protocol_drops_unstructured_data(self):
        class Worker:
            def enrollment(self, *args, progress, **kwargs):
                for item in ('place-finger', 'sample-status=1 remaining=19', 'sample-status=6 remaining=999', 'arbitrary secret text'):
                    progress(item)
                return Result('cancelled')
        self.assertEqual(self.call(['enroll', *self.args[:3]], worker=Worker()),
                         ['TOUCH', 'SAMPLE 1 19', 'RESULT cancelled'])

    def test_capture_metrics_go_only_to_diagnostic_log(self):
        class Worker:
            def verify(self, *args, progress, **kwargs):
                progress('capture-coverage=81 quality=72')
                progress('capture-coverage=81 quality=72 private text')
                progress('identify-status=2')
                progress('capture-retry=identify-quality')
                progress('capture-retry=private data')
                return Result('no-match')
        with patch('aura_fprint_bridge.syslog.syslog') as log:
            self.assertEqual(self.call(['verify', *self.args], worker=Worker()),
                             ['RESULT no-match'])
            self.assertEqual([call.args[1] for call in log.call_args_list], [
                'AURA_FPRINT_CAPTURE capture-coverage=81 quality=72',
                'AURA_FPRINT_CAPTURE identify-status=2',
                'AURA_FPRINT_CAPTURE capture-retry=identify-quality'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
