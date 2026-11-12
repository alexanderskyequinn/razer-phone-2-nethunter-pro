// SPDX-License-Identifier: LGPL-2.1-or-later
#pragma once
#include <cstdint>

// Use capture time rather than output-queue depth. Old queued images must not
// influence the newly requested lens position. Missing/unusable timestamps
// retain the previous conservative eight-frame delay.
inline bool auraFocusFrameSettled(uint64_t captured, uint64_t now,
                                  uint64_t moved, unsigned completedFrames)
{
    constexpr uint64_t settle = 80000000; // 80 ms after lens command completes
    constexpr uint64_t second = 1000000000;
    if (!captured || captured > now + second || now > captured + 10 * second)
        return completedFrames >= 8;
    return captured >= moved && captured - moved >= settle;
}
