"""Ignore an NFC interrupt after power-down instead of latching a fatal error."""
import difflib
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-mainline-6.18.2/linux')
relative = 'drivers/nfc/nxp-nci/i2c.c'
original = subprocess.check_output(['git', '-C', str(source), 'show', 'HEAD:' + relative]).decode()
needle = '''\tcase NXP_NCI_MODE_COLD:
\t\tr = -EREMOTEIO;
\t\tbreak;
'''
assert original.count(needle) == 1
updated = original.replace(needle, '''\tcase NXP_NCI_MODE_COLD:
\t\t/* A queued interrupt after power-down is not a hardware fault.
\t\t * Latching it would prevent the next normal NCI startup.
\t\t */
\t\tgoto exit_irq_handled;
''')
first_fix = updated
needle = '''\tif (r < 0)
\t\tnfc_err(&client->dev, "Unable to register IRQ handler\\n");
'''
assert updated.count(needle) == 1
updated = updated.replace(needle, '''\tif (r < 0) {
\t\tnfc_err(&client->dev, "Unable to register IRQ handler\\n");
\t\tnxp_nci_remove(phy->ndev);
\t}
''')
path = source / relative
assert path.read_text() in (original, first_fix, updated)
path.write_text(updated)
(root / 'port/nxp-nci-cold-irq.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), updated.splitlines(True), fromfile='a/'+relative, tofile='b/'+relative)))
