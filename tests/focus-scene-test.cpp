#include "../port/aura-camera-app/aura_focus_scene.h"
#include <cassert>
#include <limits>
int main()
{
    // A noisy, dark stationary scene must not keep moving the lens.
    for (int i = 0; i < 1000; ++i)
        assert(!auraFocusSceneNeedsRetry(true, 0.34 + (i % 5)*0.004,
                                        4.0 + (i % 5)*0.1, 0.35, 4.0));
    assert(auraFocusSceneNeedsRetry(true, 0.35, 20.0, 0.35, 4.0));
    assert(auraFocusSceneNeedsRetry(true, 0.7, 4.0, 0.35, 4.0));
    assert(auraFocusSceneNeedsRetry(true, 0.1, 4.0, 0.35, 4.0));
    assert(!auraFocusSceneNeedsRetry(true, 0.00001, 0.0, 0.0, 0.0));
    // Retain the existing response to contrast loss after successful focus.
    assert(auraFocusSceneNeedsRetry(false, 0.6, 50.0, 1.0, 50.0));
    assert(!auraFocusSceneNeedsRetry(false, 0.8, 50.0, 1.0, 50.0));
    assert(!auraFocusSceneNeedsRetry(true, std::numeric_limits<double>::quiet_NaN(), 5, 1, 5));
}
