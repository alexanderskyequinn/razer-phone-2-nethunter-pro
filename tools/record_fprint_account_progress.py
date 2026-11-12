"""Record tested engineering components without claiming stock authentication."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

root = Path(__file__).resolve().parents[1]
storage_log = root / 'test-runs/snapshot/fprint-account-storage-tests.txt'
worker_log = root / 'test-runs/snapshot/fprint-account-worker-tests.txt'
storage_text = storage_log.read_text(encoding='utf-8')
worker_text = worker_log.read_text(encoding='utf-8')
assert 'Ran 16 tests' in storage_text and '\nOK' in storage_text
assert 'Ran 19 tests' in worker_text and '\nOK' in worker_text
assert '/usr/local/libexec/aura-fpc-bio: OK' in worker_text
files = ['port/aura-fingerprint/aura_fprint_store.py', 'port/aura-fingerprint/aura_fprint_worker.py',
         'port/aura-fingerprint/aura_fpc_account.h', 'port/aura-fingerprint/aura_fpc_bio.c',
         'port/aura-fingerprint/aura_gatekeeper_protocol.h', 'port/aura-fingerprint/aura_gatekeeper.inc',
         'port/aura-fingerprint/aura-fprint-prompt.c', 'build/kali/fingerprint/aura-fprint-prompt',
         'build/kali/fingerprint/aura-fpc-bio']
report = {
    'updated_utc': datetime.now(timezone.utc).isoformat(),
    'stage': 'Account enrollment, prompt pipe and verification worker tested in isolation; live trial staged; stock authentication remains unfinished',
    'storage_tests': {'host_passed': 16, 'phone_passed': 16, 'data': 'synthetic only'},
    'worker_tests': {'host_passed': 19, 'phone_passed': 19, 'data': 'synthetic only'},
    'native_backend': {
        'account_path_validation': 'passed', 'account_verification_fault_tests_passed': 10,
        'account_enrollment_fault_tests_passed': 20,
        'legacy_mock_regressions': 'passed with AddressSanitizer and UndefinedBehaviorSanitizer',
        'new_modes': ['--account-check UID FINGER RECORD_ID', '--account-verify UID FINGER RECORD_ID', '--account-enroll UID FINGER RECORD_ID'],
        'parent_death_signal': 'SIGTERM; hardware cleanup uses the cancellation path',
        'installed_on_phone': False, 'real_account_template_verification': False,
        'staged_on_phone': '/var/tmp/aura-fprint-storage-check/build/kali/fingerprint/aura-fpc-bio',
        'credential_rule': 'Account enrollment verifies an existing Gatekeeper handle only; no implicit provisioning or reset',
    },
    'stock_prompt': {'library_available': 'GCR 4.4.1', 'non_secret_preview_launched': True, 'visual_check': 'pending'},
    'unchanged': ['Existing engineering fingerprint backend', 'Existing enrolled fingerprint', 'PAM/login configuration', 'System libfprint'],
    'remaining': [
        'Validate genuine secure enrollment and matching through the new native prompt path on hardware',
        'Resolve separate firmware PIN versus account password and password-change lifecycle',
        'Connect the libfprint operations and standard fprintd/Settings lifecycle',
        'Real multiple-account/finger, cancellation, deletion and rejection tests',
        'Verify PIN fallback and initial encrypted-home login before enabling unlock',
    ],
    'source_hashes': {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files},
    'evidence': [str(storage_log.relative_to(root)), str(worker_log.relative_to(root)), 'test-runs/snapshot/fprint-standard-prompt-result.txt'],
    'design': 'port/aura-fingerprint/stock-integration-design.txt',
}
prompt_text=(root/'test-runs/snapshot/fprint-standard-prompt-result.txt').read_text(encoding='utf-8')
if 'Service reached runtime time limit' in prompt_text:
    report['stock_prompt']['preview_result']='Opened, then closed by the 150-second timeout without a recorded response'
report['stock_prompt']['note']='Native GCR client and direct private-pipe transport implemented. Unprivileged prompt and root native receiver pass synthetic tests; live credential path is awaiting validation.'
layout_log=root/'test-runs/snapshot/fprint-standard-prompt-layout.txt'
if layout_log.exists() and 'PROMPT_READY' in layout_log.read_text(encoding='utf-8'):
    report['stock_prompt'].update(visual_check='Remote screenshot inspected: centered readable text and both buttons; user touch response not checked',
                                  preview_result='Closed cleanly after screenshot; no secret collected',
                                  screenshot='test-runs/snapshot/fprint-standard-prompt-layout.png')
out = root / 'build/kali/fingerprint/account-integration-progress.json'
report['stock_prompt'].update(
    native_client_preview='Opened on phone and exited on cancellation; screenshot inspected',
    live_trial='Setup PIN accepted and sensor samples received. Trial cancelled before completion; no new fingerprint committed.',
    preview_evidence='test-runs/snapshot/fprint-native-prompt-preview.txt',
    trial_evidence='test-runs/snapshot/fprint-account-trial-result.txt',
    cancellation_evidence='test-runs/snapshot/fprint-account-trial-stop.txt')
enrollment = (root/'test-runs/snapshot/fprint-account-trial-result.txt').read_text(encoding='utf-8')
positive = (root/'test-runs/snapshot/fprint-account-verify-positive-retry.txt').read_text(encoding='utf-8')
negative = (root/'test-runs/snapshot/fprint-account-verify-negative.txt').read_text(encoding='utf-8')
health = (root/'test-runs/snapshot/fprint-account-final-health.txt').read_text(encoding='utf-8')
assert 'RESULT: enrolled' in enrollment
assert re.findall(r'RESULT: ([a-z-]+)', positive)[-1] == 'match'
assert re.findall(r'RESULT: ([a-z-]+)', negative)[-1] == 'no-match'
assert 'COMMITTED_ACCOUNT_RECORDS: 1' in health and 'PENDING_RECORD: False' in health
native_log = (root/'test-runs/snapshot/fprint-native-account-tests.txt').read_text(encoding='utf-8')
assert 'Native account enrollment: 20 synthetic cases passed' in native_log
assert hashlib.sha256((root/'build/kali/fingerprint/aura-fpc-bio').read_bytes()).hexdigest() in native_log
report['stage'] = 'Standard GNOME prompt to secure account enrollment/reload/matching passed on hardware; fprintd and Settings remain unfinished'
report['native_backend']['real_account_template_verification'] = True
report['stock_prompt']['live_trial'] = 'Enrollment saved and reloaded; same finger matched on retry and a different finger was rejected. Initial same-finger attempt was a false rejection.'
report['stock_prompt']['note'] = 'Native GCR setup-PIN prompt and private pipe accepted by real secure firmware. No PIN persisted by the bridge. This remains a separate firmware setup PIN, not integrated account-password authentication.'
report['live_acceptance'] = {
    'enrollment_and_fresh_reload': True, 'correct_finger': 'match on second attempt; first attempt no-match',
    'different_finger': 'no-match', 'committed_records': 1, 'pending_records': 0,
    'system_authentication_enabled': False, 'existing_engineering_state': 'preserved',
    'limitations': ['Small manual sample only; matching reliability not established', 'No reboot test of the new account record',
                    'No multi-account/finger or deletion hardware tests', 'No fprintd/Settings or PAM wiring'],
}
report['remaining'][0] = 'Improve and validate matching reliability, including the observed first-touch false rejection'
report['evidence'] += ['test-runs/snapshot/' + name for name in (
    'fprint-native-account-tests.txt', 'fprint-native-prompt-preview.txt', 'fprint-account-trial-result.txt',
    'fprint-account-verify-positive.txt', 'fprint-account-verify-positive-retry.txt',
    'fprint-account-verify-negative.txt', 'fprint-account-final-health.txt')]
out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(out)
