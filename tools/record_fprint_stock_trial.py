"""Record the isolated stock-service trial from its concrete checks."""
from datetime import datetime, timezone
from pathlib import Path
import json
root = Path(__file__).resolve().parents[1]
def read(name): return (root/name).read_text(encoding='utf-8')
stage = read('test-runs/snapshot/fprint-candidate-stage.txt')
assert all(value in stage for value in ('DEVICES 1', 'DRIVER aura_fpc', 'STORED_RECORDS 1', 'CLOSED',
    'b0dcfc7ccdd4c946c9a6643892de4affcb37dfbe5d0ae88b5f33f6a9ef9716de'))
assert 'SANDBOX_RELOAD ready' in read('test-runs/snapshot/fprint-sandbox-check.txt')
assert 'PAM_PACKAGE_ABSENT' in read('test-runs/snapshot/fprint-stock-install.txt')
assert 'PermissionDenied' in read('test-runs/snapshot/fprint-stock-trial.txt')
assert 'has no fingers enrolled' in read('test-runs/snapshot/fprint-stock-check.txt')
tests = json.loads(read('build/kali/fingerprint/libfprint-operations-tests.json'))
assert len(tests) == 20 and set(tests.values()) == {'passed'}
health = read('test-runs/snapshot/fprint-quality-health.txt')
assert all(value in health for value in ('right-index-finger', 'COMMITTED_ACCOUNT_RECORDS 2',
    'PENDING False', 'RELOAD_FINGER 2 ready', 'RELOAD_FINGER 7 ready', 'PAM_PACKAGE_ABSENT'))
positive = read('test-runs/snapshot/fprint-stock-positive-retry.txt')
assert positive.count('Verify result: verify-no-match (done)') == 2
challenge = read('test-runs/snapshot/fprint-challenge-test-result.txt')
assert challenge.count('Verify result: verify-no-match (done)') == 1
metrics = read('test-runs/snapshot/fprint-metrics-result.txt')
assert metrics.count('Verify result: verify-no-match (done)') == 1
assert metrics.count('Verify result: verify-unknown-error (done)') == 2
assert 'capture-coverage=91 quality=34' in metrics
quality_trial = read('test-runs/snapshot/fprint-quality-result.txt')
assert 'Verify result: verify-no-match (done)' in quality_trial
assert 'identify-status=0' in quality_trial and 'capture-coverage=81 quality=58' in quality_trial
assert 'Ran 21 tests' in read('test-runs/snapshot/fprint-quality-worker-tests.txt')
assert 'Ran 10 tests' in read('test-runs/snapshot/fprint-quality-bridge-tests.txt')
report = {
    'updated_utc': datetime.now(timezone.utc).isoformat(),
    'stage': 'Stock Settings enrollment persists; valid captures still produce false rejection after verification corrections; unlock disabled',
    'packages': {'fprintd': '1.94.5-4+b2', 'libfprint-2-2': '1:1.94.10-1'},
    'operations_tests': tests,
    'candidate_manifest': json.loads(read('build/kali/fingerprint/libfprint-operations-manifest.json')),
    'temporary_service_override': '/run/systemd/system/fprintd.service.d/50-aura-candidate.conf',
    'system_library_replaced': False, 'pam_changed': False, 'fingerprint_login_enabled': False,
    'original_engineering_backend_unchanged': True, 'diagnostic_account_record_preserved': True,
    'templates_read_or_exported': False, 'stock_authorization_remote_denial_checked': True,
    'real_device_open_list_close': True, 'real_saved_record_sandbox_reload': True,
    'stock_settings_enrollment_verified': True,
    'committed_account_records': 2,
    'stock_enrollment_survives_service_restart': True,
    'fresh_reload_both_account_records': True,
    'same_finger_checks_before_quality_retry': {'attempts': 6, 'matches': 0, 'no_match': 4, 'errors': 2},
    'same_finger_checks_after_quality_retry': {'attempts': 1, 'matches': 0, 'no_match': 1},
    'verification_diagnostics': {
        'stock_auth_challenge_added': True,
        'challenge_only_trial': 'Still no match',
        'metrics': [{'coverage': 91, 'quality': 34, 'result': 'no-match'},
                    {'coverage': 81, 'quality': 58, 'identify_status': 0, 'result': 'no-match'}],
        'metrics_scale_interpretation': 'Not established; a single reading does not diagnose the rejection',
        'bounded_quality_retry_installed': True,
        'quality_retry_live_trial': 'Valid capture, status zero, still no match; live retry branch not exercised',
        'direct_backend_comparison': 'Timed out after waiting for a touch; no capture or matching outcome, retry requires user readiness',
        'native_retries': 'Up to ten recoverable captures within shared 60-second polling budget; status 2 never accepted as a match',
        'raw_images_or_templates_exported': False,
    },
    'different_finger_check_this_enrollment': 'Deferred until same-finger matching works',
    'settings_ui_trial': {
        'missing_schema_identified': True,
        'schema': 'Unmodified GNOME GDM 50.0 org.gnome.login-screen schema, test process only',
        'stock_fingerprint_row_visible': True,
        'wayland_scan_menu': 'User reported frozen UI before selecting a finger; no enrollment started',
        'xwayland_retry': 'User reaches finger selection; enrollment initially failed before capture',
        'pin_prompt_failure': 'Sandbox probe confirmed hidden desktop session bus; isolated socket bind fixes connection',
        'session_bus_fix_installed': True,
        'session_bus_scope': 'Only UID 1000, runtime override; ProtectHome=yes retained',
        'worker_tests_after_fix': 21,
        'bridge_tests_after_fix': 10,
        'enrollment_retry': 'User confirmed enrollment; stock service lists right-index-finger',
        'system_login_configuration_changed': False,
    },
    'remaining': ['Resolve same-finger false rejections, then check different-finger rejection',
                  'Real cancellation, multiple-finger/account isolation, deletion and restart recovery',
                  'Resolve Wayland finger-selection menu and package persistent stock UI/service integration',
                  'Separate firmware setup PIN versus account-password lifecycle',
                  'Login fallback and homed behavior before enabling authentication'],
    'evidence': ['test-runs/snapshot/'+name for name in ('fprint-stock-install.txt',
        'fprint-candidate-stage.txt', 'fprint-stock-trial.txt', 'fprint-stock-check.txt',
        'fprint-sandbox-check.txt', 'fprint-settings.png', 'fprint-settings-gates.txt',
        'fprint-settings-schema.png', 'fprint-settings-stall.txt', 'fprint-stall-detail.txt',
        'fprint-settings-x11-trial.txt', 'fprint-settings-enroll-failure.txt',
        'fprint-session-bus-probe.txt', 'fprint-session-bus-fix.txt',
        'fprint-settings-busfix-status.txt', 'fprint-stock-positive.txt',
        'fprint-stock-positive-retry.txt', 'fprint-stock-final-health.txt',
        'fprint-challenge-test-result.txt', 'fprint-metrics-result.txt',
        'fprint-quality-install.txt', 'fprint-quality-health.txt', 'fprint-quality-result.txt',
        'fprint-direct-comparison-result.txt',
        'fprint-quality-native-tests.txt', 'fprint-quality-worker-tests.txt',
        'fprint-quality-bridge-tests.txt')],
}
reset_path = root/'test-runs/snapshot/fprint-clear-remaining.txt'
if reset_path.exists():
    reset = reset_path.read_text(encoding='utf-8')
    assert all(value in reset for value in ('ENGINEERING_ENROLLMENT_EXISTS False',
        'COMMITTED_ACCOUNT_RECORDS 0', 'PENDING False', 'has no fingers enrolled'))
    report.update({
        'stage': 'Previous enrollments deleted at user request; fresh stock Settings enrollment pending; unlock disabled',
        'diagnostic_account_record_preserved': False,
        'committed_account_records': 0,
        'stock_settings_enrollment_verified': False,
        'fresh_enrollment_reset': {
            'user_requested': True,
            'stock_record_deleted_via_fprintd': True,
            'earlier_diagnostic_record_deleted': True,
            'original_engineering_enrollment_deleted': True,
            'firmware_setup_pin_handle_preserved': True,
            'settings_reopened': True,
            'settings_missing_row_repaired': 'Closed stale Settings instance missing candidate schema; confirmed new process uses schema and X11',
            'fresh_enrollment_result': 'Pending user completion',
            'prior_verification_results_are_historical': True,
        },
    })
    report['evidence'].extend(['test-runs/snapshot/fprint-clear-stock.txt',
                               'test-runs/snapshot/fprint-clear-remaining.txt',
                               'test-runs/snapshot/fprint-reenroll-ui-check.txt',
                               'test-runs/snapshot/fprint-reenroll-ui-fixed.txt'])
    fresh_path = root/'test-runs/snapshot/fprint-fresh-enrollment-status.txt'
    if fresh_path.exists():
        fresh = fresh_path.read_text(encoding='utf-8')
        if all(value in fresh for value in ('COMMITTED_ACCOUNT_RECORDS 1', 'PENDING False', 'right-thumb')):
            report['stage'] = 'Fresh stock Settings enrollment saved in right-thumb slot; matching check pending; unlock disabled'
            report['committed_account_records'] = 1
            report['stock_settings_enrollment_verified'] = True
            report['stock_enrollment_survives_service_restart'] = False
            report['fresh_reload_both_account_records'] = False
            report['fresh_enrollment_reset']['fresh_enrollment_result'] = 'User completed; one committed record in right-thumb slot'
            report['fresh_enrollment_reset']['physical_finger'] = 'Not confirmed for the fresh enrollment'
            report['evidence'].append('test-runs/snapshot/fprint-fresh-enrollment-status.txt')
            verification_path = root/'test-runs/snapshot/fprint-fresh-verify-result.txt'
            fresh_health_path = root/'test-runs/snapshot/fprint-fresh-health.txt'
            if verification_path.exists() and fresh_health_path.exists():
                verification = verification_path.read_text(encoding='utf-8')
                fresh_health = fresh_health_path.read_text(encoding='utf-8')
                assert 'verify-no-match (done)' in verification
                assert 'capture-coverage=100 quality=52' in verification
                assert all(v in fresh_health for v in ('COMMITTED_ACCOUNT_RECORDS 1',
                    'PENDING False', 'RELOAD_FINGER 6 ready', 'PAM_PACKAGE_ABSENT'))
                report['stage'] = 'Old prints deleted and fresh stock enrollment saved; first new-print check still no-match; survives service restart; unlock disabled'
                report['stock_enrollment_survives_service_restart'] = True
                report['fresh_enrollment_reset']['verification'] = {'attempts': 1, 'match': 0,
                    'no_match': 1, 'identify_status': 0, 'coverage': 100, 'quality': 52}
                report['fresh_enrollment_reset']['reload_after_service_restart'] = True
                report['evidence'].extend(['test-runs/snapshot/fprint-fresh-verify-result.txt',
                                           'test-runs/snapshot/fprint-fresh-health.txt'])
(root/'build/kali/fingerprint/stock-service-trial.json').write_text(json.dumps(report, indent=2)+'\n')
print(report['stage'])
