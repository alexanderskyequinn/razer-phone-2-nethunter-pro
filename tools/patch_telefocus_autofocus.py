"""Extend the existing bounded AF only to the identified telephoto/lens pair."""
from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[1]
source=Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa')
rel='src/libcamera/pipeline/simple/simple.cpp'
p=source/rel
old=p.read_text()
if 'AURA telephoto focus bounds' in old: raise SystemExit(0)
new=old.replace('int auraFocusPosition_ = 50;', 'int auraFocusPosition_ = 50;\n    int auraFocusLow_ = 50, auraFocusHigh_ = 800;')
anchor='''    auraFocusEnabled_ = swIsp_ && sensor_->model() == "imx363" && lens &&
        lens->model().find("bu64753") != std::string::npos;'''
assert anchor in new
new=new.replace(anchor,'''    // AURA telephoto focus bounds: retain the stock range for each lens.
    const bool mainLens = lens && sensor_->model() == "imx363" &&
        lens->model().find("bu64753") != std::string::npos;
    const bool teleLens = lens && sensor_->model() == "imx351" &&
        lens->model().find("lc898217") != std::string::npos;
    auraFocusEnabled_ = swIsp_ && (mainLens || teleLens);
    if (teleLens) {
        auraFocusLow_ = 60;
        auraFocusHigh_ = 610;
        auraFocusPosition_ = 60;
        auraFocus_ = AuraFocusSearch(auraFocusLow_, auraFocusHigh_);
    }''')
assert new.count('std::clamp(position, 50, 800)')==2
new=new.replace('std::clamp(position, 50, 800)','std::clamp(position, auraFocusLow_, auraFocusHigh_)')
p.write_text(new)
(root/'port/libcamera-aura-telefocus.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
print('Scoped autofocus to both known sensor/lens pairs with their own bounds')
