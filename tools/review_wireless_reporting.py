"""Check the isolated charger delta and preserve it alongside build evidence."""
import difflib
import hashlib
import json
from pathlib import Path
from charger_dc_reporting import extend_dc_reporting

root = Path(__file__).resolve().parents[1]
old = (root/'sources/charger-upstream/qcom_smbx-v15.c').read_text()
assert hashlib.sha256(old.encode()).hexdigest() == '42bc874d04bf72004896c711a9b3663f257bb9721520e702bfe48f4fee50a081'
new = extend_dc_reporting(old)
diff = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='a/drivers/power/supply/qcom_smbx.c', tofile='b/drivers/power/supply/qcom_smbx.c'))
(root/'port/qcom-smbx-wireless-reporting.patch').write_text(diff)
added = '\n'.join(line[1:] for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++'))
assert not any(word in added for word in ('regmap_write', 'regmap_update_bits', 'gpiod_set', 'regmap_bulk_write'))
old_config = (root/'build/mainline-display-fix/kernel.config').read_bytes()
new_config = (root/'build/mainline-wireless-reporting/kernel.config').read_bytes()
assert old_config == new_config, 'Kernel configuration unexpectedly changed'
assert (root/'build/mainline-wireless-reporting/sdm845-razer-aura.dtb').read_bytes() == (root/'build/kali/wireless-probe-kernel/sdm845-razer-aura.dtb').read_bytes()
report = {
    'scope': 'Only charger reporting code and kernel build metadata changed; v15 DTB and existing kernel config preserved.',
    'register_writes_added': False,
    'configuration_unchanged': True,
    'dtb_unchanged': True,
    'patch': 'port/qcom-smbx-wireless-reporting.patch',
    'source_sha256': hashlib.sha256(new.encode()).hexdigest(),
}
(root/'build/kali/wireless-reporting-review.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
