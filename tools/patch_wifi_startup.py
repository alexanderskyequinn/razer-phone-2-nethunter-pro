"""Use the stock Razer WLFW startup sequence without HOST_CAP."""
import difflib
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-mainline-6.18.2/linux')
relative = 'drivers/net/wireless/ath/ath10k/snoc.c'
original = subprocess.check_output(['git', '-C', str(source), 'show', 'HEAD:'+relative]).decode()
old = '\tif (of_property_read_bool(dev->of_node, "qcom,snoc-host-cap-skip-quirk"))'
new = '\t/* Razer stock ICNSS never sends HOST_CAP to its bundled firmware. */\n\tif (of_machine_is_compatible("razer,aura") ||\n\t    of_property_read_bool(dev->of_node, "qcom,snoc-host-cap-skip-quirk"))'
assert original.count(old) == 1
updated = original.replace(old, new)
path = source/relative
assert path.read_text() in (original, updated)
path.write_text(updated)
(root/'port/razer-wifi-startup.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), updated.splitlines(True), fromfile='a/'+relative, tofile='b/'+relative)))
