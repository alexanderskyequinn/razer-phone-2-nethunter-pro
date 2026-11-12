"""Add a machine-scoped NFC post-initialization hook on the pinned kernel."""
import difflib
import hashlib
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-mainline-6.18.2/linux')
relative = 'drivers/nfc/nxp-nci/core.c'
original = subprocess.check_output(['git','-C',str(source),'show','HEAD:'+relative]).decode()
updated = original.replace('#include <linux/delay.h>', '#include <linux/delay.h>\n#include <linux/firmware.h>\n#include <linux/of.h>')
anchor = 'static const struct nci_ops nxp_nci_ops = {'
assert updated.count(anchor) == 1
updated = updated.replace(anchor, (root/'port/nxp-nci-aura-config.c.inc').read_text() + '\n' + anchor + '\n\t.post_setup = nxp_nci_aura_post_setup,\n\t.prop_ops = nxp_nci_aura_prop_ops,\n\t.n_prop_ops = ARRAY_SIZE(nxp_nci_aura_prop_ops),')
path = source/relative
assert path.read_text() in (original, updated) or hashlib.sha256(path.read_bytes()).hexdigest() == '9f94c8062eabdbe4f432797f49a107c08faf02813551982cabaf5ad7c5f5b5e7'
path.write_text(updated)
(root/'port/nxp-nci-aura-config.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), updated.splitlines(True), fromfile='a/'+relative, tofile='b/'+relative)))
