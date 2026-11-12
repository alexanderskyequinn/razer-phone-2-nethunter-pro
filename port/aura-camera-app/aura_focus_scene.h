// SPDX-License-Identifier: LGPL-2.1-or-later
#pragma once
#include <algorithm>
#include <cmath>

// After a failed search, wait for a meaningful scene change. Retrying the same
// low-detail scene continuously cannot improve focus and causes visible hunting.
inline bool auraFocusSceneNeedsRetry(bool failed, double score, double mean,
                                    double referenceScore, double referenceMean)
{
    if (!std::isfinite(score) || !std::isfinite(mean) ||
        !std::isfinite(referenceScore) || !std::isfinite(referenceMean))
        return false;
    if (!failed)
        return score < referenceScore * 0.65;
    return std::abs(mean - referenceMean) > std::max(4.0, referenceMean * 0.25) ||
           std::abs(score - referenceScore) > std::max(0.00005, referenceScore * 0.35);
}
