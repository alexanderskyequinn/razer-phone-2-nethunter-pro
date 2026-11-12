// Synthetic optical curves exercise convergence, bounds and failure recovery.
#include "aura_focus_search.h"
#include <cassert>
#include <iostream>
#include <limits>

int main()
{
    for (int peak : {50, 125, 390, 675, 800}) {
        AuraFocusSearch search;
        int position = search.start(250), count = 0;
        while (search.state() == AuraFocusSearch::State::Coarse ||
               search.state() == AuraFocusSearch::State::Fine) {
            assert(position >= 50 && position <= 800);
            double score = 0.01 + std::exp(-std::pow((position-peak)/100.0, 2));
            auto next = search.sample(score);
            assert(next);
            position = *next;
            assert(++count <= 20);
        }
        assert(search.state() == AuraFocusSearch::State::Focused);
        assert(std::abs(position - peak) <= 13);
    }
    AuraFocusSearch flat;
    for (int peak : {60, 150, 335, 610}) {
        AuraFocusSearch tele(60, 610);
        int pos = tele.start(60), steps = 0;
        while (tele.state() == AuraFocusSearch::State::Coarse ||
               tele.state() == AuraFocusSearch::State::Fine) {
            assert(pos >= 60 && pos <= 610);
            pos = *tele.sample(0.01 + std::exp(-std::pow((pos-peak)/90.0, 2)));
            assert(++steps <= 20);
        }
        assert(tele.state() == AuraFocusSearch::State::Focused);
        assert(std::abs(pos - peak) <= 13);
    }
    int position = flat.start(400);
    while (flat.state() == AuraFocusSearch::State::Coarse)
        position = *flat.sample(0.001);
    assert(flat.state() == AuraFocusSearch::State::Failed && position == 400);
    AuraFocusSearch invalid;
    invalid.start(300);
    assert(*invalid.sample(std::numeric_limits<double>::quiet_NaN()) == 300);
    assert(invalid.state() == AuraFocusSearch::State::Failed);
    AuraFocusSearch cancelled;
    cancelled.start(450);
    cancelled.sample(0.1);
    assert(cancelled.cancel() == 450);
    assert(!cancelled.sample(0.2));
    std::cout << "Focus convergence, limits, low contrast, invalid samples and cancellation pass.\n";
}
