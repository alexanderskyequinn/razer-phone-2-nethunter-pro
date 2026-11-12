"""Headless status tests: a failed/unfinished test must never display a match."""
import importlib.machinery
import types
from pathlib import Path
import sys
import unittest

gi = types.ModuleType('gi')
gi.require_version = lambda *_: None
repo = types.ModuleType('gi.repository')
repo.Gtk = types.SimpleNamespace(Application=object)
repo.GLib = types.SimpleNamespace()
sys.modules['gi'] = gi
sys.modules['gi.repository'] = repo
source = Path(__file__).resolve().parents[1] / 'port/aura-fingerprint/aura-fingerprint-app'
module = importlib.machinery.SourceFileLoader('fingerprint_ui', str(source)).load_module()


class Widget:
    def set_text(self, text): self.text = text
    def set_fraction(self, fraction): self.fraction = fraction
    def set_sensitive(self, enabled): self.enabled = enabled


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.app = object.__new__(module.Fingerprint)
        for name in ('title', 'detail', 'progress', 'setup', 'enroll', 'verify', 'cancel'):
            setattr(self.app, name, Widget())
        self.app.final_message = False
        self.app.cancel_requested = False
        self.app.worker = object()
        self.app.total = 20

    def test_unfinished_exit_never_matches(self):
        self.app.update('MATCH: firmware identified the stored template.')
        self.app.finished(1)
        self.assertEqual(self.app.title.text, 'Test not completed')

    def test_success_requires_helper_result(self):
        self.app.update('UI_MATCH')
        self.app.finished(0)
        self.assertEqual(self.app.title.text, 'Fingerprint recognized')

    def test_no_match_is_distinct(self):
        self.app.update('UI_NO_MATCH')
        self.app.finished(3)
        self.assertEqual(self.app.title.text, 'Fingerprint not recognized')

    def test_cancel_does_not_display_late_match(self):
        self.app.cancel_requested = True
        self.app.update('UI_MATCH')
        self.app.finished(0)
        self.assertEqual(self.app.title.text, 'Test cancelled')

    def test_progress_is_bounded(self):
        self.app.update('Enrollment sample 1: status=1 remaining=19')
        self.assertAlmostEqual(self.app.progress.fraction, 0.05)
        self.app.update('Enrollment sample 2: status=6 remaining=19')
        self.assertAlmostEqual(self.app.progress.fraction, 0.05)

    def test_reload_failure_not_saved(self):
        self.app.update('ENROLLMENT_SAVED: one private template; no image exported.')
        self.app.update('UI_ERROR: The saved fingerprint could not be reloaded.')
        self.app.finished(1)
        self.assertEqual(self.app.title.text, 'Test needs attention')


if __name__ == '__main__':
    unittest.main()
