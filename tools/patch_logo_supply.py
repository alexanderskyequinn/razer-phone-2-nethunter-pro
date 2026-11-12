"""Add optional LP55xx VDD supply control required by Razer's GPIO-switched supply."""
from pathlib import Path
import difflib
import subprocess
root=Path(__file__).resolve().parents[1]
kernel=Path('/var/tmp/aura-mainline-6.18.2/linux')
path=kernel/'drivers/leds/leds-lp55xx-common.c'
before=path.read_text()
marker='\t/* Razer logo uses a separately switched supply. */'
if marker not in before:
 after=before.replace('#include <linux/slab.h>','#include <linux/slab.h>\n#include <linux/regulator/consumer.h>')
 old='\tret = lp55xx_init_device(chip);'
 assert after.count(old)==1
 after=after.replace(old,marker+'''
	ret = devm_regulator_get_enable_optional(&client->dev, "vdd");
	if (ret && ret != -ENODEV)
		return dev_err_probe(&client->dev, ret, "Failed to enable VDD supply\\n");

'''+old)
 path.write_text(after)
 (root/'port/lp55xx-vdd-supply.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/drivers/leds/leds-lp55xx-common.c',tofile='b/drivers/leds/leds-lp55xx-common.c')))
binding=kernel/'Documentation/devicetree/bindings/leds/leds-lp55xx.yaml'
text=binding.read_text()
if '  vdd-supply:' not in text:
 binding.write_text(text.replace('  label: true','  vdd-supply:\n    description: Supply powering the LED controller.\n\n  label: true'))
patch=[]
for item in (path,binding):
 rel=item.relative_to(kernel).as_posix()
 original=subprocess.check_output(['git','-c',f'safe.directory={kernel}','-C',str(kernel),'show',f'HEAD:{rel}'],text=True)
 patch.extend(difflib.unified_diff(original.splitlines(True),item.read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(root/'port/lp55xx-vdd-supply.patch').write_text(''.join(patch))
