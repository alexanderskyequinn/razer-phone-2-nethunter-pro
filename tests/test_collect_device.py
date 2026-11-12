"""Check device selection and integrity of recovery-critical backup copies."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('collect_device', Path(__file__).resolve().parents[1] / 'tools/collect_device.py')
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class CollectionTests(unittest.TestCase):
    def test_no_phone_creates_no_inventory(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(sys, 'argv', ['collect', '--adb', 'adb', '--output', temp]):
            with patch.object(collector.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'List of devices attached\n\n', '')):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    collector.main()
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_wrong_phone_is_rejected(self):
        def transport(argv, **kwargs):
            if argv[-1] == 'devices':
                return subprocess.CompletedProcess(argv, 0, 'List of devices attached\nTEST\tdevice\n', '')
            return subprocess.CompletedProcess(argv, 0, b'Other phone\n', b'')
        with tempfile.TemporaryDirectory() as temp, patch.object(sys, 'argv', ['collect', '--adb', 'adb', '--output', temp]):
            with patch.object(collector.subprocess, 'run', side_effect=transport), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                collector.main()
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_truncated_and_mismatched_backups_are_not_saved(self):
        payload = b'\x00\xff\r\n\x80 binary partition\x00'
        digest = hashlib.sha256(payload).hexdigest().encode()
        commands = []

        def transport(argv, **kwargs):
            if argv[-1] == 'devices':
                return subprocess.CompletedProcess(argv, 0, 'List of devices attached\nTEST\tdevice\n', '')
            self.assertEqual(argv[:3], ['adb', '-s', 'TEST'])
            self.assertIn(argv[3:-1], [['shell', '-T'], ['exec-out']])
            command = argv[-1]
            commands.append(command)
            if command == 'getprop ro.product.model':
                data = b'Phone 2\n'
            elif command == 'getprop ro.product.device':
                data = b'aura\n'
            elif command == 'su -c id':
                data = b'uid=0(root)\n'
            elif 'blockdev --getsize64' in command:
                data = str(len(payload)).encode()
            elif 'sha256sum /dev/block/' in command:
                data = (b'0' * 64 if 'dtbo_b' in command else digest) + b'  partition\n'
            elif 'cat /dev/block/' in command:
                data = payload[:-1] if 'boot_b' in command else payload
            else:
                return subprocess.CompletedProcess(argv, 1, b'', b'optional diagnostic unavailable')
            return subprocess.CompletedProcess(argv, 0, data, b'')

        with tempfile.TemporaryDirectory() as temp, patch.object(sys, 'argv', ['collect', '--adb', 'adb', '--output', temp, '--backup-boot']):
            with patch.object(collector.subprocess, 'run', side_effect=transport), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(collector.main(), 2)
            out = next(Path(temp).iterdir())
            self.assertEqual((out / 'boot_a.img').read_bytes(), payload)
            self.assertFalse((out / 'boot_b.img').exists())
            self.assertFalse((out / 'dtbo_b.img').exists())
            manifest = json.loads((out / 'manifest.json').read_text())
            self.assertTrue(manifest['files']['boot_a.img']['phone_sha256_verified'])
            self.assertEqual(len(list(out.glob('*.img'))), 4)
        for command in commands:
            self.assertNotRegex(command, r"(?:^|[\s;'])(flash|erase|reboot|push|dd|mount|setprop)(?:\s|$|')")


if __name__ == '__main__':
    unittest.main()
