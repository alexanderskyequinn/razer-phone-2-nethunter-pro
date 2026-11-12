"""Synthetic data only; no sensor, Gatekeeper or existing biometric state."""
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'port/aura-fingerprint/aura_fprint_store.py'
spec = importlib.util.spec_from_file_location('aura_fprint_store', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Store, StoreError = module.Store, module.StoreError


def interrupted_enrollment(path):
    s = Store(path)
    record = s.begin(1000, 'alice', 1)
    fd = os.open(record['database'], os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600, dir_fd=s.fd)
    os.write(fd, b'synthetic interrupted database')
    os.fsync(fd)
    os._exit(0)  # emulate abrupt worker death without cleanup


class StorageTests(unittest.TestCase):
    def setUp(self):
        if os.geteuid():
            self.skipTest('Requires isolated root-owned Linux scratch directory')
        self.path = tempfile.mkdtemp(prefix='aura-fprint-store-test-', dir='/var/lib')
        self.root = Path(self.path)

    def tearDown(self):
        if hasattr(self, 'path'):
            shutil.rmtree(self.path)

    def synthetic(self, record, data=b'not biometric data'):
        fd = os.open(self.root / record['database'], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, data)
        os.close(fd)

    def enroll(self, store, uid=1000, username='alice', finger=1):
        record = store.begin(uid, username, finger)
        self.synthetic(record)
        store.commit(record['database'])
        return record

    def test_accounts_fingers_and_reopen(self):
        with Store(self.path) as s:
            a = self.enroll(s)
            b = self.enroll(s, finger=2)
            c = self.enroll(s, 1001, 'bob', 1)
            self.assertEqual(len({r['database'] for r in (a, b, c)}), 3)
            self.assertEqual(len(s.list(1000, 'alice')), 2)
            self.assertEqual(s.list(1001, 'bob'), [c])
        with Store(self.path) as s:
            self.assertEqual(s.list(1001, 'bob'), [c])
            self.assertTrue(s.delete(1000, 'alice', 1))
            self.assertFalse((self.root / a['database']).exists())
            self.assertEqual(s.list(1000, 'alice'), [b])
            self.assertTrue((self.root / c['database']).exists())

    def test_cancel_preserves_committed_records(self):
        with Store(self.path) as s:
            keep = self.enroll(s)
            draft = s.begin(1000, 'alice', 2)
            self.synthetic(draft)
            s.cancel()
            self.assertEqual(s.list(1000, 'alice'), [keep])
            self.assertFalse((self.root / draft['database']).exists())

    def test_process_death_recovers_partial_enrollment(self):
        process = multiprocessing.get_context('fork').Process(target=interrupted_enrollment, args=(self.path,))
        process.start()
        process.join(10)
        self.assertEqual(process.exitcode, 0)
        self.assertEqual(len(list(self.root.glob('*.db'))), 1)
        with Store(self.path) as s:
            self.assertEqual(s.list(1000, 'alice'), [])
        self.assertEqual(list(self.root.glob('*.db')), [])

    def test_delete_io_failure_recovers_without_reexposing_record(self):
        with Store(self.path) as s:
            record = self.enroll(s)
            with patch.object(s, '_remove', side_effect=OSError('simulated failed unlink')):
                with self.assertRaises(OSError):
                    s.delete(1000, 'alice', 1)
            self.assertEqual(s.list(1000, 'alice'), [])
        with Store(self.path) as s:
            self.assertEqual(s.list(1000, 'alice'), [])
        self.assertFalse((self.root / record['database']).exists())

    def test_atomic_save_failure_keeps_prior_manifest(self):
        with Store(self.path) as s:
            record = self.enroll(s)
            with patch.object(module.os, 'replace', side_effect=OSError('simulated rename failure')):
                with self.assertRaises(OSError):
                    s.begin(1000, 'alice', 2)
        with Store(self.path) as s:
            self.assertEqual(s.list(1000, 'alice'), [record])
        self.assertEqual(list(self.root.glob('.manifest-*')), [])

    def test_lock_excludes_second_worker(self):
        with Store(self.path):
            with self.assertRaises(BlockingIOError):
                Store(self.path)

    def test_reassigned_uid_rejected(self):
        with Store(self.path) as s:
            self.enroll(s)
            for op in (lambda: s.list(1000, 'bob'), lambda: s.begin(1000, 'bob', 2), lambda: s.delete(1000, 'bob', 1)):
                with self.assertRaises(StoreError):
                    op()

    def test_invalid_identity_and_fingers(self):
        with Store(self.path) as s:
            for uid in (0, 999, -1, 0xffffffff, True, '1000'):
                with self.assertRaises(StoreError):
                    s.begin(uid, 'alice', 1)
            for name in ('../alice', 'a/b', '', 'x\n', 'x' * 65):
                with self.assertRaises(StoreError):
                    s.begin(1000, name, 1)
            for finger in (0, 11, -1, True, '1'):
                with self.assertRaises(StoreError):
                    s.begin(1000, 'alice', finger)

    def test_duplicate_and_wrong_transaction_rejected(self):
        with Store(self.path) as s:
            self.enroll(s)
            with self.assertRaises(StoreError):
                s.begin(1000, 'alice', 1)
            s.begin(1000, 'alice', 2)
            with self.assertRaises(StoreError):
                s.commit('../anything')
            with self.assertRaises(StoreError):
                s.delete(1000, 'alice', 1)

    def test_empty_large_and_public_database_rejected(self):
        with Store(self.path) as s:
            record = s.begin(1000, 'alice', 1)
            self.synthetic(record, b'')
            path = self.root / record['database']
            with self.assertRaises(StoreError):
                s.commit(record['database'])
            with path.open('wb') as f:
                f.truncate(module.MAX_DB + 1)
            with self.assertRaises(StoreError):
                s.commit(record['database'])
            path.write_bytes(b'synthetic')
            path.chmod(0o644)
            with self.assertRaises(StoreError):
                s.commit(record['database'])

    def test_symlink_and_hardlink_database_rejected(self):
        outside = self.root / 'untouched'
        outside.write_bytes(b'untouched')
        outside.chmod(0o600)
        with Store(self.path) as s:
            record = s.begin(1000, 'alice', 1)
            path = self.root / record['database']
            path.symlink_to(outside)
            with self.assertRaises(OSError):
                s.commit(record['database'])
            with self.assertRaises(StoreError):
                s.cancel()
            path.unlink()
            os.link(outside, path)
            with self.assertRaises(StoreError):
                s.commit(record['database'])
            with self.assertRaises(StoreError):
                s.cancel()
        self.assertEqual(outside.read_bytes(), b'untouched')

    def test_fifo_database_rejected_without_blocking(self):
        with Store(self.path) as s:
            record = s.begin(1000, 'alice', 1)
            os.mkfifo(self.root / record['database'], 0o600)
            with self.assertRaises(StoreError):
                s.commit(record['database'])

    def test_manifest_traversal_rejected_before_cleanup(self):
        outside = self.root / 'untouched'
        outside.write_bytes(b'untouched')
        manifest = self.root / 'manifest.json'
        manifest.write_text(json.dumps({'version': 1, 'records': [], 'pending': None, 'retired': ['../untouched']}))
        manifest.chmod(0o600)
        with self.assertRaises(StoreError):
            Store(self.path)
        self.assertEqual(outside.read_bytes(), b'untouched')

    def test_manifest_duplicate_field_and_corruption_rejected(self):
        path = self.root / 'manifest.json'
        for raw in ('{"version":1,"version":1}', '{', '[1]', 'x' * (module.MAX_MANIFEST + 1)):
            path.write_text(raw)
            path.chmod(0o600)
            with self.assertRaises((StoreError, ValueError)):
                Store(self.path)

    def test_manifest_wrong_account_filename_rejected(self):
        with Store(self.path) as s:
            self.enroll(s)
        manifest = self.root / 'manifest.json'
        state = json.loads(manifest.read_text())
        state['records'][0]['uid'] = 1001
        manifest.write_text(json.dumps(state))
        with self.assertRaises(StoreError):
            Store(self.path)

    def test_private_directory_permissions_and_symlinks(self):
        self.root.chmod(0o755)
        with self.assertRaises(StoreError):
            Store(self.path)
        self.root.chmod(0o700)
        link = self.root / 'link'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError):
            Store(str(link))
        with self.assertRaises(StoreError):
            Store(self.path + '/../' + self.root.name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
