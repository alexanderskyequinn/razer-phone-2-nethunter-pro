"""Use capture timestamps to shorten AF delay without scoring queued old frames."""
from pathlib import Path
import difflib
root=Path(__file__).resolve().parents[1]
source=Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa')
path=source/'src/libcamera/pipeline/simple/simple.cpp'
for name in ['aura_focus_timing.h','aura_focus_search.h']:
    (path.parent/name).write_bytes((root/'port/aura-camera-app'/name).read_bytes())
old=path.read_text()
if 'auraFocusFrameSettled' in old:raise SystemExit(0)
new=old
def replace(a,b):
    global new
    assert new.count(a)==1,(a,new.count(a))
    new=new.replace(a,b)
replace('#include "aura_focus_scene.h"','#include "aura_focus_scene.h"\n#include "aura_focus_timing.h"\n#include <chrono>')
replace('unsigned int auraBadFrames_ = 0;', 'unsigned int auraBadFrames_ = 0, auraFramesSinceMove_ = 0;\n    uint64_t auraMovedNs_ = 0, auraScanStartedNs_ = 0;')
replace('    auraWait_ = 8; // Existing queued frames plus mechanical settling.', '''    // AURA timestamp-based settling: exclude stale queued frames.
    auraWait_ = 0;
    auraMovedNs_ = std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
    auraFramesSinceMove_ = 0;''')
replace('        auraFocusState_ = controls::AfStateScanning;\n        auraMove', '''        auraFocusState_ = controls::AfStateScanning;
        auraScanStartedNs_ = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        auraMove''')
replace('    if (auraCooldown_) { --auraCooldown_; return; }', '''    if (auraMovedNs_) {
        const uint64_t now = std::chrono::duration_cast<std::chrono::nanoseconds>(
            std::chrono::steady_clock::now().time_since_epoch()).count();
        if (!auraFocusFrameSettled(buffer->metadata().timestamp, now, auraMovedNs_, ++auraFramesSinceMove_))
            return;
        auraMovedNs_ = 0;
    }
    if (auraCooldown_) { --auraCooldown_; return; }''')
replace('            auraCooldown_ = 120;', '            auraCooldown_ = 30;')
replace('if (auraBadFrames_ >= 20)', 'if (auraBadFrames_ >= 8)')
replace('<< " score=" << auraReference_ << " state=" << auraFocusState_;', '''<< " score=" << auraReference_ << " state=" << auraFocusState_
                << " duration_ms=" << (std::chrono::duration_cast<std::chrono::nanoseconds>(
                    std::chrono::steady_clock::now().time_since_epoch()).count() - auraScanStartedNs_) / 1000000;''')
path.write_text(new)
(root/'port/libcamera-aura-focus-timing.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/src/libcamera/pipeline/simple/simple.cpp',tofile='b/src/libcamera/pipeline/simple/simple.cpp')))
print('Prepared timestamp-gated focus timing; phone unchanged.')
