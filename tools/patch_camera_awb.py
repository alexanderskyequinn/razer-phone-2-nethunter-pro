"""Smooth preview white balance and meter the central input area, not its corner."""
from pathlib import Path
import difflib
root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa')
patch = []
def save(rel, original, new):
    (source/rel).write_text(new)
    patch.extend(difflib.unified_diff(original.splitlines(True), new.splitlines(True), fromfile='a/'+rel, tofile='b/'+rel))

rel = 'src/ipa/simple/algorithms/awb.cpp'
original = (source/rel).read_text()
if 'AURA temporal white balance' not in original:
    new = original.replace('#include <numeric>', '#include <algorithm>\n#include <numeric>')
    anchor = '\t/*\n\t * Calculate red and blue gains for AWB.'
    assert anchor in new
    new = new.replace(anchor, '''\t/* Do not learn a new white point from darkness or a covered lens. */
\tif (!nPixels || sum.g() < nPixels * 2)
\t\treturn;

''' + anchor, 1)
    old = '\tauto &gains = context.activeState.awb.gains;\n\tgains = { {\n\t\tsum.r()'
    assert old in new
    new = new.replace(old, '\tauto &gains = context.activeState.awb.gains;\n\tconst RGB<float> target = { {\n\t\tsum.r()', 1)
    anchor = '\n\tRGB<double> rgbGains'
    assert anchor in new
    new = new.replace(anchor, '''
\t/* AURA temporal white balance: low-pass valid statistics and bound
\t * each update, so a new object cannot instantly tint the preview. */
\tfor (unsigned int i = 0; i < 3; ++i) {
\t\tfloat next = gains[i] + 0.15f * (target[i] - gains[i]);
\t\tgains[i] = std::clamp(next, gains[i] * 0.9f, gains[i] * 1.1f);
\t}
''' + anchor, 1)
    save(rel, original, new)

rel = 'src/libcamera/software_isp/debayer_egl.cpp'
original = (source/rel).read_text()
if 'AURA input-area metering' not in original:
    old = '''\t/*
\t * Don't pass x,y from window_ since process() already adjusts for it.
\t * But crop the window to 2/3 of its width and height for speedup.
\t */
\tstats_->setWindow(Rectangle(window_.size()));'''
    assert old in original
    new = original.replace(old, '''\t/* AURA input-area metering: GPU output is scaled, while CPU stats
\t * receive the entire raw buffer with no crop-offset adjustment.
\t * Sample the central two thirds of the input, independent of preview
\t * size, instead of a preview-sized rectangle in the upper-left. */
\tconst unsigned int meterWidth = inputCfg.size.width * 2 / 3;
\tconst unsigned int meterHeight = inputCfg.size.height * 2 / 3;
\tstats_->setWindow(Rectangle((inputCfg.size.width - meterWidth) / 2,
\t\t\t\t    (inputCfg.size.height - meterHeight) / 2,
\t\t\t\t    meterWidth, meterHeight));''', 1)
    save(rel, original, new)
if patch:
    (root/'port/libcamera-aura-metering.patch').write_bytes(''.join(patch).encode())
