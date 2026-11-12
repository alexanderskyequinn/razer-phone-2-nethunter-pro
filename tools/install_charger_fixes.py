"""Apply reviewed charger corrections to this port's pinned kernel tree."""
from pathlib import Path
import subprocess
import sys
from charger_dc_reporting import extend_dc_reporting
source = Path(sys.argv[1]).resolve()
assert str(source) == '/var/tmp/aura-mainline-6.18.2/linux'
name = 'drivers/power/supply/qcom_smbx.c'
original = subprocess.check_output(['git', '-C', str(source), 'show', 'HEAD:' + name]).decode()
text = original
changes = [
    ('return !!(reg & mask);', 'return !!(val & mask);'),
    ('smb_set_current_limit(chip, current_ua);', 'smb_set_current_limit(chip, min(current_ua,\n\t\t(unsigned int)chip->batt_info->constant_charge_current_max_ua));'),
    ('rc = (chip->batt_info->voltage_max_design_uv - 3487500) / 7500 + 1;',
     'rc = chip->batt_info->constant_charge_voltage_max_uv;\n\tif (rc == -EINVAL)\n\t\trc = chip->batt_info->voltage_max_design_uv;\n\trc = (rc - 3487500) / 7500 + 1;'),
    ('1950000 / CURRENT_SCALE_FACTOR);', 'min(1950000, chip->batt_info->constant_charge_current_max_ua) /\n\t\t\t  CURRENT_SCALE_FACTOR);'),
]
for old, new in changes:
    assert text.count(old) == 1, old
    text = text.replace(old, new)
old = '''switch (stat) {
	case SMB2_CHARGER_ERROR_STATUS_BAT_OV_BIT:
		*val = POWER_SUPPLY_HEALTH_OVERVOLTAGE;
		return 0;
	case SMB2_BAT_TEMP_STATUS_TOO_COLD_BIT:
		*val = POWER_SUPPLY_HEALTH_COLD;
		return 0;
	case SMB2_BAT_TEMP_STATUS_TOO_HOT_BIT:
		*val = POWER_SUPPLY_HEALTH_OVERHEAT;
		return 0;
	case SMB2_BAT_TEMP_STATUS_COLD_SOFT_LIMIT_BIT:
		*val = POWER_SUPPLY_HEALTH_COOL;
		return 0;
	case SMB2_BAT_TEMP_STATUS_HOT_SOFT_LIMIT_BIT:
		*val = POWER_SUPPLY_HEALTH_WARM;
		return 0;
	default:
		*val = POWER_SUPPLY_HEALTH_GOOD;
		return 0;
	}'''
new = '''if (stat & SMB2_CHARGER_ERROR_STATUS_BAT_OV_BIT)
		*val = POWER_SUPPLY_HEALTH_OVERVOLTAGE;
	else if (stat & SMB2_BAT_TEMP_STATUS_TOO_HOT_BIT)
		*val = POWER_SUPPLY_HEALTH_OVERHEAT;
	else if (stat & SMB2_BAT_TEMP_STATUS_TOO_COLD_BIT)
		*val = POWER_SUPPLY_HEALTH_COLD;
	else if (stat & SMB2_BAT_TEMP_STATUS_HOT_SOFT_LIMIT_BIT)
		*val = POWER_SUPPLY_HEALTH_WARM;
	else if (stat & SMB2_BAT_TEMP_STATUS_COLD_SOFT_LIMIT_BIT)
		*val = POWER_SUPPLY_HEALTH_COOL;
	else
		*val = POWER_SUPPLY_HEALTH_GOOD;
	return 0;'''
assert text.count(old) == 1
text = text.replace(old, new)
path = source / name
base_text = text
text = extend_dc_reporting(text)
assert path.read_text() in (original, base_text, text), 'Unexpected local charger edits'
path.write_text(text)
root = Path(__file__).resolve().parents[1]
patch = subprocess.check_output(['git', '-C', str(source), 'diff', '--', name])
(root / 'port/qcom-smbx-bringup.patch').write_bytes(patch)
