"""Keep the kernel's LC898217XC driver, adding Razer module initialization."""
from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[1]
src=Path('/var/tmp/aura-mainline-6.18.2/linux/drivers/media/i2c/lc898217xc.c')
old=src.read_text()
s=old.replace('#include <linux/module.h>', '#include <linux/module.h>\n#include <linux/of.h>')
s=s.replace('struct regmap *regmap;', 'struct regmap *regmap;\n\tbool aura;')
anchor='\tusleep_range(8000, 10000);\n\treturn 0;'
assert anchor in s
s=s.replace(anchor,'''\tusleep_range(8000, 10000);
    if (lc898217xc->aura) {
        u64 value;
        int tries;
        ret = cci_read(lc898217xc->regmap, CCI_REG8(0xf0), &value, NULL);
        if (ret) goto power_error;
        if (value != 0x72) { ret = -ENODEV; goto power_error; }
        ret = cci_write(lc898217xc->regmap, CCI_REG8(0xe0), 1, NULL);
        if (ret) goto power_error;
        for (tries = 0; tries < 100; ++tries) {
            ret = cci_read(lc898217xc->regmap, CCI_REG8(0xe3), &value, NULL);
            if (ret) goto power_error;
            if (value == 0) return 0;
            usleep_range(1000, 1500);
        }
        ret = -ETIMEDOUT;
        goto power_error;
    }
    return 0;
power_error:
    regulator_bulk_disable(ARRAY_SIZE(lc898217xc_supply_names), lc898217xc->supplies);
    return ret;''')
s=s.replace('LC898217XC_MIN_FOCUS_POS,\n', '(lc898217xc->aura ? 60 : LC898217XC_MIN_FOCUS_POS),\n')
s=s.replace('LC898217XC_MAX_FOCUS_POS,\n', '(lc898217xc->aura ? 610 : LC898217XC_MAX_FOCUS_POS),\n')
s=s.replace('LC898217XC_FOCUS_STEPS, 0);', 'LC898217XC_FOCUS_STEPS, lc898217xc->aura ? 60 : 0);')
s=s.replace('/* Initialize subdev */\n\tv4l2_i2c_subdev_init', 'lc898217xc->aura = of_device_is_compatible(dev->of_node, "razer,aura-lc898217xc");\n\n\t/* Initialize subdev */\n\tv4l2_i2c_subdev_init',1)
s=s.replace('{ .compatible = "onnn,lc898217xc" },', '{ .compatible = "razer,aura-lc898217xc" },\n\t{ .compatible = "onnn,lc898217xc" },')
s=s.replace('\t__v4l2_ctrl_handler_setup(&lc898217xc->ctrls);\n\n\treturn ret;', '\tret = __v4l2_ctrl_handler_setup(&lc898217xc->ctrls);\n\tif (ret) lc898217xc_power_off(lc898217xc);\n\treturn ret;')
out=root/'port/aura-native-telefocus'
out.mkdir(exist_ok=True)
(out/'lc898217xc.c').write_text(s)
(out/'Makefile').write_text('obj-m += lc898217xc.o\n')
(root/'port/lc898217xc-aura.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/drivers/media/i2c/lc898217xc.c',tofile='b/drivers/media/i2c/lc898217xc.c')))
