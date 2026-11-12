"""Avoid repeated AF sweeps on unchanged scenes after failed focus."""
from pathlib import Path
import difflib
root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa')
path = source / 'src/libcamera/pipeline/simple/simple.cpp'
header = root / 'port/aura-camera-app/aura_focus_scene.h'
(path.parent / header.name).write_bytes(header.read_bytes())
old = path.read_text()
if 'auraFocusSceneNeedsRetry' in old:
    raise SystemExit(0)
new = old.replace('#include "aura_focus_search.h"', '#include "aura_focus_search.h"\n#include "aura_focus_scene.h"')
new = new.replace('double auraScoreSum_ = 0, auraReference_ = 0;', 'double auraScoreSum_ = 0, auraReference_ = 0, auraReferenceMean_ = 0;')
new = new.replace('auraReference_ = auraFocus_.score();', 'auraReference_ = auraFocus_.score();\n            auraReferenceMean_ = mean / count;')
anchor = 'if (score < auraReference_ * 0.65 || auraFocusState_ == controls::AfStateFailed)'
assert anchor in new
new = new.replace(anchor, 'if (auraFocusSceneNeedsRetry(auraFocusState_ == controls::AfStateFailed,\n                                    score, mean / count, auraReference_, auraReferenceMean_))')
assert new != old
path.write_text(new)
(root/'port/libcamera-aura-focus-retry.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='a/src/libcamera/pipeline/simple/simple.cpp', tofile='b/src/libcamera/pipeline/simple/simple.cpp')))
