from pathlib import Path
import tarfile
root=Path(__file__).resolve().parents[1]
for name in ('pack_kali_boot.py','run_kali_boot_update.py','monitor_kali_trial.py'):
    path=root/'tools'/name
    text=path.read_text()
    if "'v10'" not in text:
        path.write_text(text.replace("'v9'", "'v9', 'v10'"))
with tarfile.open(root/'build/kali/radio-update-v10.tar','w') as tar:
    for name in ('hci_uart','btqca'):
        path=root/'build/kali/peripheral-modules/drivers/bluetooth'/f'{name}.ko.zst'
        tar.add(path,arcname=f'lib/modules/6.18.2-aura-bringup1+/kernel/drivers/bluetooth/{name}.ko.zst')
    tar.add(root/'build/kali/upstream-radio-firmware/qcom/sdm845/mba.mbn',arcname='lib/firmware/qcom/sdm845/razer/aura/mba.mbn')
