#include "../port/aura-camera-app/aura_focus_timing.h"
#include "../port/aura-camera-app/aura_focus_search.h"
#include "../port/aura-camera-app/aura_focus_scene.h"
#include <cassert>
#include <cmath>
#include <limits>
int main()
{
    const uint64_t moved=20000000000ULL;
    assert(!auraFocusFrameSettled(moved-1,moved+100000000,moved,100));
    assert(!auraFocusFrameSettled(moved+79000000,moved+100000000,moved,100));
    assert(auraFocusFrameSettled(moved+80000000,moved+100000000,moved,1));
    assert(!auraFocusFrameSettled(0,moved+100000000,moved,7));
    assert(auraFocusFrameSettled(0,moved+100000000,moved,8));
    assert(!auraFocusFrameSettled(moved+999000000000ULL,moved,moved,7));
    assert(!auraFocusFrameSettled(1,moved,moved,7));
    for (auto bounds : {std::pair{50,800},std::pair{60,610}}) {
        for (int target=bounds.first;target<=bounds.second;target+=7) {
            AuraFocusSearch search(bounds.first,bounds.second);
            int pos=search.start(bounds.first),samples=0;
            while(search.state()==AuraFocusSearch::State::Coarse || search.state()==AuraFocusSearch::State::Fine) {
                assert(pos>=bounds.first && pos<=bounds.second);
                // Broad and narrow unimodal contrast peaks across both lens ranges.
                auto next=search.sample(0.01+std::exp(-std::pow((pos-target)/75.0,2)));
                assert(++samples<=18);
                if(next)pos=*next;
            }
            assert(search.state()==AuraFocusSearch::State::Focused);
            assert(std::abs(pos-target)<=13);
        }
        AuraFocusSearch flat(bounds.first,bounds.second);
        int original=bounds.first+30;auto next=flat.start(original);
        while(flat.state()==AuraFocusSearch::State::Coarse)next=*flat.sample(0.1);
        assert(flat.state()==AuraFocusSearch::State::Failed && next==original);
        flat.start(original);assert(flat.cancel()==original);
        flat.start(original);assert(*flat.sample(std::numeric_limits<double>::quiet_NaN())==original);
        assert(flat.state()==AuraFocusSearch::State::Failed);
    }
}
