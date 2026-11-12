"""Record exact telephony bring-up evidence without claiming working calls."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
refs=root/'sources/qcom-ims-reference'
source_base='https://raw.githubusercontent.com/David112x/android-firmware-qti-sdm660/master/LINUX/android/vendor/qcom/proprietary/ims-ship/qmi/'
sources=[{'file':str(p.relative_to(root)).replace('\\','/'),'url':source_base+p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(refs.glob('*.[ch]'))]
report={
 'packages':{'81voltd':'1.2.0-2','gnome-calls':'50.0-1','chatty':'0.8.9-2'},
 'installation':'Phone package audit clean; 81voltd enabled and running. Calls and Chatty user services active. Same packages installed into local build root and recipes updated; no full image regenerated.',
 'package_archive':{'path':'build/kali/telephony-packages.tar','sha256':hashlib.sha256((root/'build/kali/telephony-packages.tar').read_bytes()).hexdigest()},
 'diagnostic_binaries':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'build/kali/cellular').glob('aura-ims*'))},
 'verified':[
  'Subscription 0 binding fixes InvalidOperation on fresh IMS/IMSA queries. Subscription 1 is not applicable.',
  'ModemManager exposes Voice and Messaging interfaces. 81voltd advertises IMS Data service 770 version 1.',
  'CDMAless-Verizon carrier profile is already active; IMS APN is already configured. No carrier profiles modified.',
  'Standard IMS service and SMS enable request accepted. Direct GET 0x90 confirms VoLTE, IMS mobile data, normal registration and SMS over IP all enabled.',
  'NAS voice preference ps-preferred; LTE network advertises IMS voice support. Existing ps-only/data-centric LTE setup retained.',
  'Temporary ModemManager IMS IPv6 bearer connected successfully on qmapmux0.1 while internet bearer remained present. IMSA still reported no IMS PDP after 15 seconds. Test bearer disconnected and deleted successfully.',
 ],
 'diagnostic_correction':{
  'library':'libqmi 1.38.0',
  'problem':'IMS settings GET response TLV IDs for registration/SMS are off by one in the library. Its registration getter reads 0x18 (Wi-Fi provisioning string), SMS reads 0x1A (UT flag). Correct IDs are 0x19 and 0x1B. Therefore original claims that SMS was disabled or failed to enable were not valid evidence.',
  'confirmed_by':['https://raw.githubusercontent.com/linux-mobile-broadband/libqmi/1.38.0/data/qmi-service-ims.json','https://raw.githubusercontent.com/linux-mobile-broadband/libqmi/main/data/qmi-service-ims.json'],
  'workaround':'Use direct protocol values from aura-ims-legacy-probe for settings. IMSA registration status definition matches the reference and direct read confirms not registered.',
  'rollback_warning':'Original sms-off helper option was based on invalid getter baseline and has been removed from source/build and temporary phone binary. Actual pre-enable SMS/registration values were not recorded correctly. Later normal-off/enable cycle started from directly verified enabled state and restored it.',
 },
 'current_blocker':'Incoming plain SMS did not arrive per user. Direct IMSA response: not registered, IMS PDP disconnected, registration/PDP errors both zero, even after standard IMS off/on cycle. IMS APN bearer connects, but modem IMS does not claim it. Keeping the IMS settings control client open during the bounded test also did not trigger registration. Calls and emergency calling not validated.',
 'user_context':'User has not tested this Verizon SIM in the Razer under Android. LTE data is user-verified; carrier voice compatibility remains unconfirmed.',
 'evidence':['telephony-offline-install-result-final.txt','ims-bound-probe.txt','ims-after-radio-refresh-settled.txt','ims-enable-test.txt','ims-complete-enable-flags.txt','imsa-pdp-probe.txt','ims-carrier-profile.txt','voice-preference.txt','ims-cycle-result.txt','ims-bearer-result.txt','ims-hold-during.txt','telephony-final-lte-health-retry.txt','telephony-finished-health.txt'],
 'cleanup':'90-second held-client process completed with exit 0. Temporary IMS bearer removed. Temporary verbose 81voltd override removed and normal daemon restarted. Final package audit clean, IMS enabled flags retained, internet connected, desktop/boost active and SSH USB-only.',
 'ims_data_startup':'Modem sends IMSDCM 0x23 link-local address, 0x2e Bluetooth-event registration and 0x34 service-enable mask. 81voltd treats these as generic success. Reference declares only result mandatory for all three; no evidence yet these acknowledgements prevent registration. No 0x20 PDP-start request observed.',
 'next_work':'Trace the remaining modem IMS initialization requirements and AP/client startup sequence. Do not change carrier profiles or NV fields speculatively; correct Verizon profile is active and IMS APN connection already succeeds.',
 'references':sources,
 'access':'SSH remains USB-only. No calls or texts sent by the agent. Final LTE health check passed on retry: home/connected, interface-bound HTTPS 200, desktop/CPU boost active, SSH bound 192.0.2.1:22.',
}
for p in sorted(refs.glob('*.cpp')):
 module = 'uim' if p.name.startswith('qcril_uim') else 'ims' if p.name.startswith('qcril_qmi_ims') else 'qmi'
 report['references'].append({'file':p.relative_to(root).as_posix(),'url':source_base.replace('ims-ship/qmi/',f'qcril-hal/modules/{module}/src/')+p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
report['startup_followup'] = {
 'policy':'Direct GETs: network service mask 0x1f, cellular preferred, LTE allowed by RAT mask 0x644e; WWAN/WLAN IMS blocking masks both zero. IMS active on primary subscription. These are local modem states, not successful network registration.',
 'sim':'USIM ready, ISIM detected, both PIN1 disabled. Qualcomm qcril_uim_card.cpp maps ISIM DETECTED to READY when PIN1 is disabled/verified. No SIM session or content changes made.',
 'reference_comparison':'Stock Imss/Imsa endpoints bind primary subscription exactly as diagnostic does. New stock IMS registration path uses SET0x8f ims_service_enabled, matching our enable command.',
 'bounded_test':'Both IMSA0x22 and IMS0x2a event subscriptions accepted; normal-registration=true reasserted. Monitor held both clients for 60 seconds and exited0. Received IMS settings-change0x91 only; no IMSA events observed. Final direct queries still not registered/no IMS PDP/errors0.',
 'health':'LTE home/connected and interface-bound HTTPS200 verified after test; Phosh/CPU boost active and SSH bound only192.0.2.1. No reboot, flash, carrier profile or SIM changes.',
 'domain_observation':'Final NAS preference is data-centric/cs-ps/ps-preferred, although earlier startup helper had verified ps-only. Cause/timing not established. Old health script stopped at its ps-only assertion; updated observational health check passed LTE HTTPS. Domain not rewritten while LTE remains healthy.',
 'next':'Trace why modem policy never requests an IMS data connection despite active subscription and enabled registration. Carrier IMS provisioning versus remaining modem/host integration is not yet distinguished; do not infer a carrier rejection from zero error codes.',
}
report['evidence'] += ['ims-continuation-baseline.txt','ims-policy-probe.txt','ims-active-policy-probe.txt','ims-sim-readiness.txt','ims-startup-monitor-launch.txt','ims-startup-result-final.txt','ims-continuation-health-final.txt']
report['cleanup'] += ' Stock-style event monitor completed and released both clients; no persistent startup change added in this follow-up.'
(root/'build/kali/telephony-progress.json').write_text(json.dumps(report,indent=2)+'\n')
