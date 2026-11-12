"""Keep this work's checked changes distinct from untested hardware claims."""
from pathlib import Path
from datetime import datetime,timezone
import json
root=Path(__file__).resolve().parents[1]
checks=(root/'test-runs/snapshot/apps-final-check.txt').read_text()
assert '"completed": true' in checks and 'PACKAGE_AUDIT' in checks and 'CAMERAS' in checks
assert 'ActiveState=active' in (root/'test-runs/snapshot/apps-ui-check.txt').read_text()
assert '33408184320' in (root/'test-runs/snapshot/apps-cleanup.txt').read_text()
result={
 'updated_utc':datetime.now(timezone.utc).isoformat(),
 'requested_app_selection':json.loads((root/'port/app-packages.json').read_text()),
 'apps':{'state':'installed and package-verified','source':'Official Kali signed catalog',
         'public_package_count':1700,'archive_bytes':1990973440,
         'archive_sha256':'5cb654adb97863c269432c702c5f03b92ee09fe799ce4746011d824dcfe7e33b',
         'offline_usb_cache_imported':True,'repository_keyring_repaired':True,
         'phosh_show_all_apps_enabled':True,'package_completion_verified':True,
         'dpkg_audit_clean':True,'apt_dependency_check_passed':True,
         'mobile_settings_installed':True,'calculator_launch_visually_verified':True,
         'software_process_launch_passed':True,'software_catalog_visually_verified':False,
         'temporary_phone_downloads_removed':True,'root_available_bytes':33408184320,
         'existing_boot_image_unchanged':True},
 'main_camera_startup':{
   'found':'Sensor ID read 0x333 once at startup; existing driver rejected it. A later reprobe returned the correct 0x363 and bound.',
   'change':'Keep reset asserted until clock is ready; retain stock 11 ms reset settling; at most three strict ID reads.',
   'installed':True,'module_sha256':'5a426de89a882eb2de9d7b87abc0d76e203b20e4b85a42acd8c068ff2a44a424',
   'rollback_on_phone':'/var/lib/aura/imx363-before-startup-retry.ko',
   'fault_tests':7,'live_rebind_cycles_passed':3,'both_rear_sensors_enumerate':True,
   'reboot_tested':False,'stream_test_after_change':False,
   'old_driver_removal_warning':'Clock enable warning occurred during removal of old module; no new warnings in the later runtime check.'},
 'wifi':{'small_download_slow':True,'power_save_original':'on',
         'bounded_comparison_bytes':323040,'power_save_on_seconds':2.688117,'power_save_off_seconds':1.445830,
         'power_save_restored':True,'sustained_bandwidth_established':True,
         'larger_download_bytes':2974796,'larger_power_save_on_seconds':12.938826,
         'larger_power_save_off_seconds':12.847592,
         'conclusion':'Slow public download path confirmed; disabling power save did not materially improve the larger transfer. Cause unresolved.'},
 'hardware_video':json.loads((root/'test-runs/snapshot/apps-hardware-video.txt').read_text()),
 'remaining_hardware_report':'build/kali/hardware-audit.html',
 'future_image':{'recipes_updated':True,'apps_and_camera_candidate_rebuilt':False},
 'evidence':['test-runs/snapshot/apps-hardware-inventory.txt','test-runs/snapshot/apps-repository-key-repair.txt',
             'test-runs/snapshot/apps-cache-import.txt','test-runs/snapshot/apps-camera-startup-install.txt',
             'test-runs/snapshot/apps-codec-camera-inventory.txt','test-runs/snapshot/apps-wifi-throughput.txt',
             'test-runs/snapshot/apps-wifi-larger-download.txt','test-runs/snapshot/apps-final-check.txt',
             'test-runs/snapshot/apps-ui-check.txt','test-runs/snapshot/apps-calculator.png',
             'test-runs/snapshot/apps-cleanup.txt','test-runs/snapshot/apps-hardware-video.txt']
}
(root/'build/kali/apps-hardware-progress.json').write_text(json.dumps(result,indent=2)+'\n')
status_path=root/'port-status.json'
status=json.loads(status_path.read_text())
history=status.setdefault('historical_status_summaries',[])
if 'v18.' in status.get('status','') and status['status'] not in history:history.append(status['status'])
status['status']='Persistent native Kali/Phosh and NetHunter on v26. Everyday stock apps and kali-linux-default installed and package-checked; about 32 GiB free. Main camera reset timing fixed and three rebind cycles passed; reboot acceptance pending. H.264 hardware encode/decode passed a 60-frame synthetic test. Fingerprint secure matching works but stock enrollment/unlock integration remains incomplete. See current hardware audit for remaining capabilities; SIM work remains deferred.'
status.setdefault('current_followup',{})['apps_and_hardware']='build/kali/apps-hardware-progress.json'
status['current_followup']['hardware_audit']='build/kali/hardware-audit.json'
status['next_milestones']=[
 'Integrate stock fingerprint enrollment and unlock with the existing secure matching backend',
 'Validate camera startup after reboot, persist telephoto focus fixes, and test video/OIS/flash',
 'Investigate Wi-Fi throughput and perform power/suspend endurance testing',
 'Diagnose front camera, ambient light/proximity and remaining peripheral modes',
 'Rebuild and hardware-test the clean install image with stock setup and key-free recovery']
status_path.write_text(json.dumps(status,indent=2)+'\n')
print('Recorded completed app installation and bounded hardware checks; release image rebuild remains pending.')
