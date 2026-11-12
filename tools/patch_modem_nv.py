"""Reproduce Razer's original reserved-memory assignment before modem start."""
import difflib
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-mainline-6.18.2/linux')
relative = 'drivers/remoteproc/qcom_q6v5_mss.c'
original = subprocess.check_output(['git', '-C', str(source), 'show', 'HEAD:'+relative]).decode()
anchor = 'static int q6v5_start(struct rproc *rproc)'
assert original.count(anchor) == 1
updated = original.replace(anchor, (root/'port/qcom-q6v5-aura-nv.c.inc').read_text()+'\n'+anchor)
start = updated.index(anchor)
part = updated[start:]
old = '\tret = q6v5_mba_load(qproc);'
assert old in part
part = part.replace(old, '\tret = q6v5_aura_assign_nv(qproc);\n\tif (ret)\n\t\treturn ret;\n\n'+old, 1)
updated = updated[:start] + part
path = source/relative
assert path.read_text() in (original, updated)
path.write_text(updated)
(root/'port/razer-modem-nv-memory.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), updated.splitlines(True), fromfile='a/'+relative, tofile='b/'+relative)))
