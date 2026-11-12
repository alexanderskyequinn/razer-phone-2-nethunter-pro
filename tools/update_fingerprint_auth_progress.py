"""Record verified setup status; never reads phone PINs or biometric data."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / 'build/kali/fingerprint-progress.json'
data = json.loads(path.read_text())
data['updated_utc'] = datetime.now(timezone.utc).isoformat()
data['status'] = 'Secure PIN setup, enrollment, saved-template reload and user match/rejection tests passed. User-approved permanent storage configuration installed and verified after service restart. Desktop unlock is not enabled; full phone reboot not yet tested.'
data['next_steps'] = [
    'Integrate verified matching with desktop fingerprint services',
    'Investigate explicit local raw-image export through stock engineering commands; not executed',
]
data['current_kernel']['built_in_app_client'] = 'Named resident-app lookup; keymaster64 client tested successfully'
data['transport_evidence']['basis'] = 'Offline stock HAL analysis and real-device firmware, capture and enrollment-sample tests'
manifest = json.loads((root / 'build/kali/fingerprint-app-manifest.json').read_text())
data['enrollment_test']['diagnostic_sha256'] = 'b0dcfc7ccdd4c946c9a6643892de4affcb37dfbe5d0ae88b5f33f6a9ef9716de'
data['enrollment_test']['app_bundle_sha256'] = manifest['sha256']
data['enrollment_test']['native_executable_updated_separately'] = False
data['enrollment_test']['real_templates_enrolled'] = 1
data['enrollment_test']['sample_submissions'] = None
data['enrollment_test']['final_sample_attempt'] = 21
data['enrollment_test']['finish_enrollment_status'] = 0
data['enrollment_test']['fresh_session_reload_passed'] = True
data['enrollment_test']['private_database_bytes'] = 68637
data['device_mutations'] = 'v26 fingerprint resources, root-only TEE, stock signed firmware and GPIO driver. User authorized PIN setup and enrollment; one private template saved and reloaded on phone. No raw images or template contents exported. Desktop authentication unchanged. Permanent on-demand RPMB listener configuration installed with explicit user approval; runtime override removed.'
data['prepared_persistent_bundle'] = {
    'sha256': manifest['sha256'],
    'installed': True,
    'explicit_user_approval': True,
    'status': 'Installed and verified after service restart without runtime override. Started on demand by Fingerprint app, not automatically at boot. Full phone reboot not performed.',
}
data['hardware_validation']['wrapped_hardware_auth_key_initialization'] = True
data['hardware_validation']['gatekeeper_pin_enrollment_status'] = 0
data['hardware_validation']['gatekeeper_handle_saved'] = True
data['hardware_validation']['gatekeeper_pin_verification_status'] = 0
data['hardware_validation']['fpc_gatekeeper_authorization_status'] = 0
data['hardware_validation']['enrollment'] = True
data['hardware_validation']['fresh_session_database_reload'] = True
data['hardware_validation']['matching'] = True
data['hardware_validation']['matching_evidence'] = {
    'enrolled_finger_match': 'User confirmed',
    'different_finger_rejected': 'User confirmed; latest native result NO_MATCH and UI_NO_MATCH',
    'scope': 'One user-reported same/different-finger pair; not a false-accept-rate or spoof-resistance assessment',
}
data['gatekeeper_analysis'] = {
    'driver_copy_explicitly_approved': True,
    'driver_sha256': hashlib.sha256((root / 'build/kali/fingerprint/android.hardware.gatekeeper@1.0-impl-qti.so').read_bytes()).hexdigest(),
    'helper_library_copy_approval_pending': False,
    'helper_library_copy_explicitly_approved_and_completed': True,
    'stock_protocol_negotiation_hardware_passed': True,
    'resident_public_versions': {'api': '3.0', 'ta': '3.132'},
    'pin_storage': 'Not saved or logged; masked UI, stdin pipes, core dumps disabled',
    'user_id': 1000,
    'android_primary_user_modified': False,
    'simulations': 'ASan/UBSan wire bounds, full setup, Gatekeeper rejection, challenge mismatch and FPC authorization rejection passed; 6 UI status tests passed',
}
data['rpmb_diagnostic'] = {
    'status': 'Authenticated relay passed real Gatekeeper PIN setup and verification; fingerprint firmware accepted the resulting authorization',
    'reference_commit': 'e5e4e7ca1c39505076a43d66afb2f8da31f56c24',
    'interface': '/dev/bsg/0:0:0:49476',
    'public_capabilities_read_passed': True,
    'counter_query_hardware_passed': True,
    'counter_query_nonce_matched': True,
    'counter_query_mac_verified_by_probe': False,
    'capacity_bytes': 16777216,
    'max_transfer_frames': 64,
    'listener_id': 8192,
    'read_only_phase_binary_sha256': 'f9a9b657a2c6f179948d69e4d3674562fdbb391ebf0ac9ad8f9a53074d889509',
    'binary_sha256': '5b515613e73cd70c574d8342547269c8722b994c0cd953a593e8f73148324a1b',
    'writes': 'Only intact secure-firmware authenticated type-3 transactions; key programming prohibited; no retries',
    'write_hardware_validated': True,
    'tests': 'ASan/UBSan read regression and mocked 1/2-frame writes, frame preservation, key prohibition, bounds, inconsistent batch metadata, all transport failure stages without retries',
    'frame_data_logged': False,
    'boot_enabled': False,
    'configuration_persistent': True,
    'runtime_override_present': False,
    'rollback': 'diagnostic/kali-fingerprint-storage-rollback.sh',
}
for evidence in ('fpc-auth-preflight-result.txt', 'gatekeeper-stock-disassembly.txt',
                 'fingerprint-app-v3-install.txt', 'fingerprint-app-v3-result.txt',
                 'fingerprint-app-v4-install.txt', 'fingerprint-app-v4-result.txt',
                 'keymaster-buffer-disassembly.txt', 'gatekeeper-failure-state.txt',
                 'fingerprint-app-v5-result.txt', 'keymaster-ta-disassembly.txt',
                 'rpmb-interface-check.txt', 'ufs-capabilities.txt', 'rpmb-readonly-start.txt',
                 'rpmb-counter-check.txt', 'rpmb-readonly-result-latest.txt',
                 'rpmb-authenticated-start.txt', 'rpmb-authenticated-result.txt',
                 'fingerprint-secure-ready.txt', 'fingerprint-reload-failure.txt',
                 'fingerprint-reload-detail.txt', 'fingerprint-reload-fixed-check.txt',
                 'fingerprint-reload-fix-install.txt', 'fingerprint-matching-confirmed.txt',
                 'fingerprint-permanent-install.txt'):
    entry = 'test-runs/snapshot/' + evidence
    if entry not in data['evidence']:
        data['evidence'].append(entry)
path.write_text(json.dumps(data, indent=2) + '\n')
print('Fingerprint progress updated: saved-template reload and user match/rejection tests passed; desktop unlock disabled.')
