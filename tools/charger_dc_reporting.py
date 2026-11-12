"""Read-only wireless input reporting for the Razer's PMI8998 charger."""

def extend_dc_reporting(text):
    def replace(old, new):
        nonlocal text
        assert text.count(old) == 1, old
        text = text.replace(old, new)

    replace('struct smb_chip {', '''/* Razer P9221 output feeds PMI8998 DCIN. Reporting only: no DC writes. */
#define AURA_DCIN_RT_STS 0x410
#define AURA_DCIN_PLUGIN BIT(4)
#define AURA_USE_DCIN BIT(3)

struct smb_chip {''')
    replace('\tstruct power_supply *chg_psy;\n};', '''	struct power_supply *chg_psy;
	struct power_supply *dc_psy;
	struct delayed_work dc_report_work;
	bool dc_supported;
	int dc_last_state;
};''')
    replace('static int smb_get_prop_status(struct smb_chip *chip, int *val)', '''static int smb_get_prop_dc_online(struct smb_chip *chip, int *val)
{
	unsigned int stat;
	int rc;

	*val = 0;
	if (!chip->dc_supported)
		return 0;
	rc = regmap_read(chip->regmap, chip->base + POWER_PATH_STATUS(chip), &stat);
	if (rc)
		return rc;
	*val = !!(stat & AURA_USE_DCIN) &&
	       !!(stat & P_PATH_VALID_INPUT_POWER_SOURCE_STS_BIT);
	return 0;
}

static int smb_get_prop_status(struct smb_chip *chip, int *val)''')
    replace('''	u32 stat;
	int usb_online = 0;
	int rc;

	rc = smb_get_prop_usb_online(chip, &usb_online);
	if (!usb_online) {''', '''	u32 stat;
	int usb_online = 0, dc_online = 0;
	int rc;

	rc = smb_get_prop_usb_online(chip, &usb_online);
	if (rc)
		return rc;
	if (!usb_online) {
		rc = smb_get_prop_dc_online(chip, &dc_online);
		if (rc)
			return rc;
	}
	if (!usb_online && !dc_online) {''')
    replace('static int smb_probe(struct platform_device *pdev)', '''static enum power_supply_property aura_dc_properties[] = {
	POWER_SUPPLY_PROP_PRESENT,
	POWER_SUPPLY_PROP_ONLINE,
};

static int aura_dc_get_property(struct power_supply *psy,
			       enum power_supply_property prop,
			       union power_supply_propval *val)
{
	struct smb_chip *chip = power_supply_get_drvdata(psy);
	unsigned int stat;
	int rc;

	switch (prop) {
	case POWER_SUPPLY_PROP_ONLINE:
		return smb_get_prop_dc_online(chip, &val->intval);
	case POWER_SUPPLY_PROP_PRESENT:
		rc = regmap_read(chip->regmap, chip->base + AURA_DCIN_RT_STS, &stat);
		if (rc)
			return rc;
		val->intval = !!(stat & AURA_DCIN_PLUGIN);
		return 0;
	default:
		return -EINVAL;
	}
}

static const struct power_supply_desc aura_dc_desc = {
	.name = "pmi8998-wireless",
	.type = POWER_SUPPLY_TYPE_WIRELESS,
	.properties = aura_dc_properties,
	.num_properties = ARRAY_SIZE(aura_dc_properties),
	.get_property = aura_dc_get_property,
};

static void aura_dc_report_work(struct work_struct *work)
{
	struct smb_chip *chip = container_of(to_delayed_work(work),
					    struct smb_chip, dc_report_work);
	unsigned int present;
	int online, status, state;

	if (regmap_read(chip->regmap, chip->base + AURA_DCIN_RT_STS, &present) ||
	    smb_get_prop_dc_online(chip, &online) ||
	    smb_get_prop_status(chip, &status))
		goto requeue;
	state = (!!(present & AURA_DCIN_PLUGIN)) | (online << 1) | (status << 2);
	if (state != chip->dc_last_state) {
		chip->dc_last_state = state;
		power_supply_changed(chip->dc_psy);
		/* The fuel gauge caches STATUS from this existing charger supply. */
		power_supply_changed(chip->chg_psy);
	}
requeue:
	queue_delayed_work(system_freezable_wq, &chip->dc_report_work,
			   msecs_to_jiffies(2000));
}

static int smb_probe(struct platform_device *pdev)''')
    replace('\tchip->gen = match_data->gen;', '''	chip->gen = match_data->gen;
	/* This board's DC input is physically wired to its Qi receiver. */
	chip->dc_supported = chip->gen == SMB2 &&
			     of_machine_is_compatible("razer,aura");
	chip->dc_last_state = -1;''')
    replace('\t/* Initialise charger state */', '''	if (chip->dc_supported) {
		struct power_supply_config dc_config = { .drv_data = chip };

		chip->dc_psy = devm_power_supply_register(chip->dev, &aura_dc_desc,
							&dc_config);
		if (IS_ERR(chip->dc_psy))
			return dev_err_probe(chip->dev, PTR_ERR(chip->dc_psy),
					     "Failed to register wireless input\\n");
		rc = devm_delayed_work_autocancel(chip->dev, &chip->dc_report_work,
						  aura_dc_report_work);
		if (rc)
			return rc;
		queue_delayed_work(system_freezable_wq, &chip->dc_report_work, 0);
	}

	/* Initialise charger state */''')
    return text
