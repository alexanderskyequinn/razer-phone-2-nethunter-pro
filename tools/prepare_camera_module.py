"""Carry minimal power-error handling fixes on the pinned IMX363 driver."""
from pathlib import Path
import difflib
import re
root = Path(__file__).resolve().parents[1]
original = (root/'sources/imx363-v6.18.2.c').read_text()
patched = original.replace('GPIOD_OUT_LOW);', 'GPIOD_OUT_HIGH);')
old = '\t\tdev_err(dev, "failed to enable clock\\n");\n\t\tregulator_bulk_disable(IMX363_NUM_SUPPLIES, imx363->supplies);\n'
new = '\t\tdev_err(dev, "failed to enable clock\\n");\n\t\tgpiod_set_value_cansleep(imx363->reset_gpio, 1);\n\t\tregulator_bulk_disable(IMX363_NUM_SUPPLIES, imx363->supplies);\n\t\treturn ret;\n'
assert old in patched
patched = patched.replace(old, new)
patched = patched.replace('\tgpiod_set_value_cansleep(imx363->reset_gpio, 0);\n\n\tret = clk_prepare_enable', '\tret = clk_prepare_enable')
patched = patched.replace('\tusleep_range(1000, 1200);', '\tusleep_range(1000, 1200);\n\tgpiod_set_value_cansleep(imx363->reset_gpio, 0);\n\t/* Razer\'s retained module sequence waits 11 ms after reset release. */\n\tusleep_range(11000, 12000);')
old_id='\tint ret;\n\tu64 val;\n\n\tret = cci_read(imx363->regmap, IMX363_REG_CHIP_ID,\n\t\t       &val, NULL);'
new_id='\tint ret, attempt;\n\tu64 val = 0;\n\n\t/* A transient read must not permanently hide the camera for this boot. */\n\tfor (attempt = 0; attempt < 3; attempt++) {\n\t\tret = cci_read(imx363->regmap, IMX363_REG_CHIP_ID,\n\t\t\t       &val, NULL);\n\t\tif (!ret && val == IMX363_CHIP_ID)\n\t\t\treturn 0;\n\t\tif (attempt < 2)\n\t\t\tusleep_range(10000, 11000);\n\t}'
assert patched.count(old_id)==1
patched=patched.replace(old_id,new_id)
# The inherited 1080p table is incomplete; it returns a cropped/blank image.
# Expose only the stock-sized mode that has delivered a verified full frame.
patched, count = re.subn(r'\n\t\{\n\t\t\.width = 1920,.*?\n\t\},', '', patched, count=1, flags=re.S)
assert count == 1
out = root/'port/aura-camera'
out.mkdir(exist_ok=True)
(out/'imx363.c').write_bytes(patched.encode())
(out/'Makefile').write_bytes(b'obj-m += imx363.o\n')
(root/'port/imx363-power-handling.patch').write_bytes(''.join(difflib.unified_diff(original.splitlines(True), patched.splitlines(True), fromfile='a/drivers/media/i2c/imx363.c', tofile='b/drivers/media/i2c/imx363.c')).encode())
