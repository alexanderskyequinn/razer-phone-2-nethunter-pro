"""Record actual storage/recovery milestones without claiming pending work passed."""
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
state = {
    'updated_utc': datetime.now(timezone.utc).isoformat(),
    'filesystem_expansion': {
        'completed': True, 'partition': 'userdata', 'partition_bytes': 50132250624,
        'filesystem_blocks': 12239319, 'block_bytes': 4096,
        'df_summary': '46G total, 5.6G used, 41G free',
        'partition_table_unchanged': True, 'ext4_errors': 0,
        'evidence': 'test-runs/snapshot/storage-expansion-result.txt',
    },
    'desktop_storage': {
        'internal_ufs_hidden': True, 'microSD_visible': True,
        'rule': 'port/kali-overlay/etc/udev/rules.d/99-aura-internal-storage.rules',
        'evidence': 'test-runs/snapshot/internal-storage-hidden.txt',
    },
    'android_userspace_dependency': {
        'vendor_unmounted': True, 'other_android_filesystems_mounted': False,
        'configuration_references_found': False,
        'external_firmware_symlinks_found': False,
        'desktop_wifi_bluetooth_and_fingerprint_service_active': True,
        'fingerprint_database_reload_without_vendor': True,
        'cold_boot_without_vendor_tested': True,
        'unused_android_system_vendor_oem_bytes': 12884901888,
        'unused_partitions_reclaimed': False,
        'essential_firmware_and_calibration_partitions_retained': True,
        'evidence': 'test-runs/snapshot/android-vendor-unmounted.txt',
    },
    'recovery': {
        'installed_slot': 'a', 'kali_slot': 'b',
        'installed_sha256': 'a87cbd126bf0fac48378b4e2c76fa96853c21f3d4d3f25caef40dfb7b68039d9',
        'first_test': 'USB NCM network appeared; screen black; SSH refused. User returned to Download Mode.',
        'status': 'Old slot-switching regression repaired from verified same-phone GPT metadata. Corrected timed and final untimed images passed recovery-to-Kali round trips and live partition metadata comparison. Final recovery and authenticated desktop shortcut installed; phone left in healthy Kali.',
        'screen_user_verified': True,
        'volume_navigation_user_verified': True,
        'ssh_verified': True,
        'offline_filesystem_check_exit': 0,
        'kali_return_verified': True,
        'final_untimed_image_return_verified': True,
        'desktop_shortcut_installed': True,
        'test_timeout_seconds': 0,
        'original_vbmeta_b_restored_after_approved_diagnostic': True,
        'corrected_selector_sha256': '62eef5f012d76c93579b9c1e2fb20c209e3649f4747b345c5a2d4f6f394d8773',
        'boot_image_b_restored_sha256': '2fdfb649c979f70ebc44c82c9d33c9a7580e2f67e2e798b5f9567a8396cd8abd',
        'evidence': ['test-runs/snapshot/rescue-fixed-health-retry.txt',
                     'test-runs/snapshot/kali-after-fixed-recovery.txt',
                     'test-runs/snapshot/kali-fixed-roundtrip-gpt.json',
                     'test-runs/snapshot/rescue-final-health.txt',
                     'test-runs/snapshot/recovery-desktop-install.txt',
                     'test-runs/snapshot/kali-after-final-recovery.txt',
                     'test-runs/snapshot/kali-final-roundtrip-gpt.json'],
        'backup_directory_on_phone': '/var/lib/aura/recovery-rollbacks',
        'new_build_manifest': 'build/kali/rescue/manifest.json',
    },
    'installer': {
        'release_image_completed': False,
        'remaining': ['Rebuild a clean image with current hardware fixes and no personal data',
                      'Add automatic filesystem expansion and first-run setup',
                      'Test fresh installation and return-to-Kali paths'],
    },
}
(root/'build/kali/native-storage-progress.json').write_text(json.dumps(state,indent=2)+'\n')
print('Recorded verified storage milestones and incomplete recovery/installer work.')
