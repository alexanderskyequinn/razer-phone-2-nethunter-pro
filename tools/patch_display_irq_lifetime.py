"""Preserve IRQ indices until the encoder's resource-disable stage uses them."""
import difflib
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-mainline-6.18.2/linux')
relative = 'drivers/gpu/drm/msm/disp/dpu1/dpu_encoder_phys_cmd.c'
original = subprocess.check_output(['git', '-C', str(source), 'show', 'HEAD:'+relative]).decode()
old = '\tphys_enc->irq[INTR_IDX_CTL_START] = 0;\n\tphys_enc->irq[INTR_IDX_PINGPONG] = 0;\n\tphys_enc->irq[INTR_IDX_RDPTR] = 0;\n\n'
assert original.count(old) == 1
updated = original.replace(old, '')
path = source/relative
assert path.read_text() in (original, updated)
path.write_text(updated)
(root/'port/dpu-preserve-irq-indices.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), updated.splitlines(True), fromfile='a/'+relative, tofile='b/'+relative)))
