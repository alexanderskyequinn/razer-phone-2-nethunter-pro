// SPDX-License-Identifier: LGPL-2.1-or-later
// Bounded contrast search. Hardware integration must supply settled samples.
#pragma once
#include <algorithm>
#include <cmath>
#include <optional>
#include <vector>

class AuraFocusSearch {
public:
    enum class State { Idle, Coarse, Fine, Focused, Failed };

    explicit AuraFocusSearch(int low = 50, int high = 800)
        : low_(low), high_(high) {}

    int start(int current)
    {
        original_ = std::clamp(current, low_, high_);
        best_ = original_;
        bestScore_ = -1;
        worstScore_ = 1e9;
        state_ = State::Coarse;
        candidates_.clear();
        for (int p = low_; p < high_; p += 100)
            candidates_.push_back(p);
        candidates_.push_back(high_);
        index_ = 0;
        return candidates_[index_];
    }

    // Each call represents a newly settled lens position, not each video frame.
    std::optional<int> sample(double score)
    {
        if (state_ != State::Coarse && state_ != State::Fine)
            return {};
        if (!std::isfinite(score) || score < 0) {
            state_ = State::Failed;
            return original_;
        }
        if (score > bestScore_) {
            bestScore_ = score;
            best_ = candidates_[index_];
        }
        worstScore_ = std::min(worstScore_, score);
        if (++index_ < candidates_.size())
            return candidates_[index_];

        if (state_ == State::Coarse) {
            // No useful peak: return to the starting position, avoid arbitrary
            // near-focus selection from image noise or a uniform/covered lens.
            if (bestScore_ < 0.00005 || bestScore_ < worstScore_ * 1.12) {
                state_ = State::Failed;
                return original_;
            }
            state_ = State::Fine;
            candidates_.clear();
            const int begin = std::max(low_, best_ - 50);
            const int end = std::min(high_, best_ + 50);
            for (int p = begin; p < end; p += 25)
                candidates_.push_back(p);
            candidates_.push_back(end);
            index_ = 0;
            // Fine sweep needs its own comparison baseline if exposure drifted.
            bestScore_ = -1;
            return candidates_[index_];
        }
        state_ = State::Focused;
        return best_;
    }

    int cancel()
    {
        state_ = State::Idle;
        return original_;
    }
    State state() const { return state_; }
    int best() const { return best_; }
    double score() const { return bestScore_; }

private:
    int low_, high_, original_ = 50, best_ = 50;
    double bestScore_ = -1, worstScore_ = 1e9;
    State state_ = State::Idle;
    std::vector<int> candidates_;
    size_t index_ = 0;
};
