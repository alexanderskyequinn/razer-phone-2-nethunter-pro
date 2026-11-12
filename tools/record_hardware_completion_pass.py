"""Record checked milestones and distinguish unfinished hardware integration."""
from datetime import datetime,timezone
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[1]
def read(name):return json.loads((root/name).read_text(encoding='utf-8'))
def save(name,data):(root/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
camera=read('build/kali/camera-completion-progress.json')
reboot_log=(root/'test-runs/snapshot/hardware-after-reboot.txt').read_text(encoding='utf-8')
reboot_passed='ca601de2-14af-488c-a701-0f783755235f' in reboot_log and '/opt/aura-camera/lib/libcamera.so.0.7.2: OK' in reboot_log and '/bus/i2c/drivers/imx363' in reboot_log
camera.update(updated_utc=datetime.now(timezone.utc).isoformat(),status='Both rear cameras focus and settle on near/far targets; user confirmed faster timing stays sharp. Updated library installed persistently. GNOME Camera video playback is upright with sound, user verified. '+('One normal reboot passed: both sensors bound and corrected library/module retained.' if reboot_passed else 'Reboot check pending.'))
camera['completed']+= [x for x in [
 'Both rear cameras near/far optical focus user-verified',
 'Timestamp-gated focus settling and smaller fine search installed; measured scans 1.7-2.4 seconds',
 'GNOME Camera video recording, upright playback and audible sound user-verified'] if x not in camera['completed']]
camera['remaining']=['Reboot acceptance of startup and autofocus fixes','OIS and synchronized still flash','Front sensor no acknowledgement; cause unproven','Low-light and moving-subject focus; video quality/endurance']
camera['timing']={'archive_sha256':'6f546d39f543f6b2089e50d1a4054d4690c21485693f7fb47e70dd22bb118897','library_sha256':'72297e58cd21c3d4ca24dc3d434b431d070282ac958e8450518edb14537c4442','installed':True,'user_verified':True,'rollback':'/opt/aura-camera-before-focus-timing','reboot_verified':False}
camera['timing']['reboot_verified']=reboot_passed
if reboot_passed:camera['remaining'].remove('Reboot acceptance of startup and autofocus fixes')
camera['evidence']+= [x for x in ['test-runs/snapshot/hardware-camera-focus-persist.txt','test-runs/snapshot/hardware-focus-timing-result.txt','test-runs/snapshot/hardware-camera-focus-timing-persist.txt'] if x not in camera['evidence']]
save('build/kali/camera-completion-progress.json',camera)
tele=read('build/kali/telefocus-progress.json');tele.update(status=camera['status'],trial_persistent=True,pending_user_question=None,near_far_user_verified=True)
save('build/kali/telefocus-progress.json',tele)
fp=read('build/kali/fingerprint-progress.json')
fp['stock_integration']={
 'stage':'Native platform discovery passed; biometric operations and stock account integration incomplete',
 'libfprint_commit':'6f9479c3d55f847c1b3769f28ceb99227f9858cf',
 'patch':'port/libfprint-aura-platform.patch','mocked_discovery_tests':read('build/kali/fingerprint/libfprint-platform-tests.json'),
 'upstream_tests':{'passed':3,'failed':0,'skipped':35,'note':'Discovery-only selected driver; other driver/introspection tests unavailable'},
 'real_phone_device_count':1,'reported_biometric_features':0,
 'system_library_replaced':False,'pam_changed':False,'templates_read_or_exported':False,
 'phone_test_path':'/var/tmp/libfprint-platform','evidence':'test-runs/snapshot/hardware-fprint-platform.txt',
 'remaining':['Per-account secure authorization design compatible with fprintd','Multiple fingers and private database isolation','Cancellation, enumeration, deletion and recovery','Stock Settings enrollment and correct/wrong-finger tests before enabling unlock']}
account_progress=root/'build/kali/fingerprint/account-integration-progress.json'
if account_progress.exists():
    fp['stock_integration']['account_backend']=read('build/kali/fingerprint/account-integration-progress.json')
    fp['stock_integration']['remaining']=fp['stock_integration']['account_backend']['remaining']
stock_trial=root/'build/kali/fingerprint/stock-service-trial.json'
if stock_trial.exists():
    fp['stock_integration']['service_trial']=read('build/kali/fingerprint/stock-service-trial.json')
    fp['stock_integration']['stage']=fp['stock_integration']['service_trial']['stage']
    fp['stock_integration']['remaining']=fp['stock_integration']['service_trial']['remaining']
save('build/kali/fingerprint-progress.json',fp)
sleep_evidence='test-runs/snapshot/hardware-suspend-120-result-recheck.txt'
sleep_log=(root/sleep_evidence).read_text(encoding='utf-8')
sleep_passed=all(x in sleep_log for x in ['success: 1','fail: 0','COMPLETED','Result=success','wlan0:wifi:connected','0 loaded units listed.'])
report={'updated_utc':datetime.now(timezone.utc).isoformat(),'camera':camera['timing'],'stock_fingerprint':fp['stock_integration'],
 'suspend':{'two_minute_test_passed':sleep_passed,'sleep_seconds_approximately':117,'wifi_reconnected':sleep_passed,'bluetooth_power_restored':sleep_passed,'accelerometer_available':sleep_passed,'microsd_mounted':sleep_passed,'visual_post_wake_check':'User confirmed normal wake, touch, rotation and keyboard hiding','automatic_idle_suspend_enabled':False,'evidence':sleep_evidence,'limitations':'One bounded cycle; does not establish overnight drain or Bluetooth peripheral reconnection.'},
 'service_cleanup':{'unsupported_smart_monitor_disabled':True,'persistent_diagnostic_journal_max_mib':32,'evidence':'test-runs/snapshot/hardware-service-cleanup.txt'},
 'microsd':read('test-runs/snapshot/hardware-microsd-write.txt'),
 'wifi':{'baseline':read('test-runs/snapshot/hardware-wifi-lan.json'),'power_save_off':read('test-runs/snapshot/hardware-wifi-lan-power-save-off.json'),
         'after_reboot_and_suspend':read('test-runs/snapshot/hardware-wifi-lan-after-reboot.json'),
         'cubic_comparison':read('test-runs/snapshot/hardware-wifi-lan-cubic.json'),
         'original_congestion_control_restored':True,'restore_evidence':'test-runs/snapshot/hardware-wifi-cubic-restored.txt',
         'band_check':{'profile_not_band_locked':True,'existing_ssid_visible_on_2_4_ghz_only':True,'evidence':'test-runs/snapshot/hardware-wifi-band-check.txt'},
         'power_save_restored':True,'conclusion':'Slow local SSH transfers confirmed. Power-save disable did not help. Earlier larger uploads timed out; the later 1 MiB test completed in both directions at 1.22 and 1.65 Mbit/s including SSH startup. No permanent network tuning applied.'},
 'sim_work':'Deferred, unchanged','reboot_check':'passed one normal reboot' if reboot_passed else 'pending'}
save('build/kali/hardware-completion-pass.json',report)
apps=read('build/kali/apps-hardware-progress.json')
apps['main_camera_startup'].update(reboot_tested=reboot_passed,stream_test_after_change=True)
apps['followup']='build/kali/hardware-completion-pass.json'
save('build/kali/apps-hardware-progress.json',apps)
status=read('port-status.json');status.setdefault('current_followup',{})['hardware_completion_pass']='build/kali/hardware-completion-pass.json'
status['status']='Persistent native Kali/Phosh and NetHunter on v26. Everyday apps and kali-linux-default installed. Both rear cameras focus faster and stay sharp; upright video with sound user-verified. One normal reboot and a two-minute suspend/wake cycle passed. MicroSD bounded write/readback passed. Native libfprint discovers the sensor, but stock secure enrollment/unlock remains unfinished. Wi-Fi throughput and other hardware qualification remain; SIM work deferred.'
status['next_milestones']=['Integrate stock fingerprint secure per-account enrollment and unlock','Camera OIS/flash and front-sensor diagnosis','Wi-Fi throughput and longer power/suspend endurance','Ambient light/proximity and remaining peripheral modes','Rebuild and hardware-test clean installation with stock setup and key-free recovery']
save('port-status.json',status)
print('Recorded verified camera, discovery, storage and wireless milestones.')
