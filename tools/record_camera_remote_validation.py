"""Record remote camera checks without upgrading physical validation claims."""
import json
from datetime import datetime, timezone
from pathlib import Path
root = Path(__file__).resolve().parents[1]
now = datetime.now(timezone.utc).isoformat()
log = root/'test-runs/snapshot/rear-camera-focus-retry-check.txt'
rows = [json.loads(line) for line in log.read_text().splitlines() if line.startswith('{')]
results = [row for row in rows if row.get('result') == 'stream_pass']
assert len(results) == 2
status = ('Both rear streams and 640x360 VP8 encode/decode passed ~40-second checks at ~30fps. '
          'Dark-scene focus retry correction passed on phone; telephoto stopped repeated hunting. '
          'Updated userspace remains a runtime trial pending well-lit near/far optical validation.')
remaining = ['Well-lit telephoto near/far focus and main-camera regression check, then persist trial',
             'GNOME Camera video/audio/orientation and OIS validation',
             'Front sensor does not acknowledge; physical supply/module health unresolved',
             'Fingerprint QSEECOM transport, board driver and FPC userspace integration']
for name in ('telefocus-progress.json','camera-completion-progress.json'):
    p=root/'build/kali'/name
    data=json.loads(p.read_text())
    data.update(updated_utc=now,status=status,remaining=remaining)
    if name.startswith('telefocus'):
        data.update(trial_prefix='/opt/aura-camera-focus-retry-test',
                    trial_sha256='359e0ec60714198f892787d3d20c7ee9f69a9e940476d5b8bb7b2b04c9f97b97',
                    trial_archive='build/kali/camera/aura-libcamera-focus-retry-trial.tar.gz',
                    trial_persistent=False)
    data['remote_video_checks']=results
    data.setdefault('evidence',[]).extend(['test-runs/snapshot/rear-camera-stream-check.txt',
                                          'test-runs/snapshot/rear-camera-focus-retry-check.txt'])
    p.write_text(json.dumps(data,indent=2)+'\n')
fp={
  'updated_utc':now,'status':'Integration requirements identified; fingerprint not operational',
  'sensor':'Stock DTS file names FPC1235; compatible fpc,fpc1020. Physical sensor ID not read.',
  'reset_gpio':95,'interrupt_gpio':121,
  'firmware_app':'fpctzappfingerprint',
  'firmware_present':True,
  'stock_hal_dependencies':['libQSEEComAPI.so','libbinder.so','libutils.so','Android bionic','/dev/ion'],
  'transport_evidence':{'QSEECom_start_app_buffer_bytes':128,'QSEECom_send_modified_cmd_request_bytes':64,
                        'response_bytes':64,'shared_buffer_patch_offset':4,
                        'basis':'Offline disassembly of retained stock fingerprint.sdm845.so; not exercised'},
  'current_kernel':{'qseecom_version':'0x1400000','board_allowlisted':False,
                    'userspace_device':False,'dynamic_trusted_app_loader':False,
                    'built_in_app_client':'uefisecapp only'},
  'candidate_transport':{'url':'https://github.com/wrobelda/goodix-fp-spi-linux',
                         'kernel_branch':'https://github.com/wrobelda/linux/tree/qcom-qseecom-tee',
                         'supplicant':'https://github.com/wrobelda/qsee-supplicant',
                         'status':'Reference only. Reported on SM8250/Goodix, not validated for this SDM845/FPC device.'},
  'next_steps':['Review/backport named-app loading, shared-memory patching and listener support',
                'Adapt stock reset/interrupt platform support to current kernel',
                'Verify FPC command ABI and implement Linux userspace adapter',
                'Run sensor identity and transport tests with physical recovery available before enrollment'],
  'evidence':['test-runs/snapshot/camera-fingerprint-preflight.txt','test-runs/snapshot/fingerprint-elf-dependencies.txt',
              'sources/razer-kernel-reference/fingerprint-fpc1235.dtsi',
              'sources/razer-kernel-reference/fpc1020-misc-platform-tee.c'],
  'device_mutations':'None for fingerprint; no templates, enrollment, secure storage or TrustZone calls changed'
}
fp['evidence'][2]='sources/razer-kernel-reference/arch/arm64/boot/dts/qcom/fih/rc2/fingerprint-fpc1235.dtsi'
(root/'build/kali/fingerprint-progress.json').write_text(json.dumps(fp,indent=2)+'\n')
print('Recorded camera validation and fingerprint integration requirements')
