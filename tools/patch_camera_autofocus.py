"""Experimental IMX363/BU64753 contrast AF, scoped to this hardware pair."""
from pathlib import Path
import difflib
import shutil
root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa')
path = source / 'src/libcamera/pipeline/simple/simple.cpp'
original = path.read_text()
shutil.copyfile(root / 'port/aura-camera-app/aura_focus_search.h', path.parent / 'aura_focus_search.h')
if 'AURA bounded contrast autofocus' in original:
    print('Autofocus patch already present')
    raise SystemExit(0)
new = original.replace('#include "libcamera/internal/camera.h"', '#include "libcamera/internal/camera.h"\n#include "libcamera/internal/camera_lens.h"\n#include "libcamera/internal/mapped_framebuffer.h"\n#include "libcamera/internal/dma_buf_allocator.h"\n#include "aura_focus_search.h"')
new = new.replace('#include <libcamera/stream.h>', '#include <libcamera/stream.h>\n#include <libcamera/formats.h>')
anchor = '\tSimpleFrames frameInfo_;'
assert anchor in new
new = new.replace(anchor, anchor + '''

    // AURA bounded contrast autofocus: keep the device-specific prototype
    // confined to the known main sensor/lens pair and stock DAC range.
    bool auraFocusEnabled_ = false;
    int auraFocusMode_ = controls::AfModeContinuous;
    int auraFocusPosition_ = 50;
    int auraFocusState_ = controls::AfStateIdle;
    unsigned int auraWait_ = 20, auraSamples_ = 0, auraCooldown_ = 0;
    unsigned int auraBadFrames_ = 0;
    double auraScoreSum_ = 0, auraReference_ = 0;
    bool auraPending_ = true;
    AuraFocusSearch auraFocus_;
    void auraFocusControls(const ControlList &controls);
    void auraFocusBuffer(FrameBuffer *buffer);
    bool auraMove(int position);
''', 1)
anchor = '\tvideo_ = pipe->video(entities_.back().entity);'
assert anchor in new
new = new.replace(anchor, '''    auto *lens = sensor_->focusLens();
    auraFocusEnabled_ = swIsp_ && sensor_->model() == "imx363" && lens &&
        lens->model().find("bu64753") != std::string::npos;
    if (auraFocusEnabled_) {
        ControlInfoMap::Map map(controlInfo_.begin(), controlInfo_.end());
        map[&controls::AfMode] = ControlInfo(controls::AfModeValues);
        map[&controls::AfTrigger] = ControlInfo(controls::AfTriggerValues);
        controlInfo_ = ControlInfoMap(std::move(map), controls::controls);
        LOG(SimplePipeline, Info) << "AURA contrast autofocus available";
    }

''' + anchor, 1)
anchor = '\t/* Complete the buffer and the request. */\n\tRequest *request = buffer->request();'
assert anchor in new
new = new.replace(anchor, '\tauraFocusBuffer(buffer);\n\n' + anchor, 1)
anchor = '\nvoid SimpleCameraData::ispStatsReady'
assert anchor in new
functions = r'''
bool SimpleCameraData::auraMove(int position)
{
    const int ret = sensor_->focusLens()->setFocusPosition(std::clamp(position, 50, 800));
    if (ret) {
        auraFocusState_ = controls::AfStateFailed;
        auraPending_ = false;
        auraFocus_.cancel();
        LOG(SimplePipeline, Error) << "AURA lens movement failed: " << ret;
        return false;
    }
    auraFocusPosition_ = std::clamp(position, 50, 800);
    auraWait_ = 8; // Existing queued frames plus mechanical settling.
    auraSamples_ = 0;
    auraScoreSum_ = 0;
    return true;
}

void SimpleCameraData::auraFocusControls(const ControlList &ctrls)
{
    if (!auraFocusEnabled_)
        return;
    if (auto mode = ctrls.get(controls::AfMode)) {
        if (*mode != auraFocusMode_) {
            auraFocusMode_ = *mode;
            auraFocus_.cancel();
            auraFocusState_ = controls::AfStateIdle;
            auraPending_ = *mode == controls::AfModeContinuous;
        }
    }
    if (auto trigger = ctrls.get(controls::AfTrigger)) {
        if (*trigger == controls::AfTriggerStart && auraFocusMode_ == controls::AfModeAuto)
            auraPending_ = true;
        if (*trigger == controls::AfTriggerCancel) {
            if (auraFocusState_ == controls::AfStateScanning)
                auraMove(auraFocus_.cancel());
            auraPending_ = false;
            auraFocusState_ = controls::AfStateIdle;
        }
    }
}

void SimpleCameraData::auraFocusBuffer(FrameBuffer *buffer)
{
    if (!auraFocusEnabled_ || !buffer->request())
        return;
    auto &metadata = buffer->request()->_d()->metadata();
    metadata.set(controls::AfState, auraFocusState_);
    if (buffer->metadata().status != FrameMetadata::FrameSuccess ||
        auraFocusMode_ == controls::AfModeManual)
        return;
    const auto &buffers = buffer->request()->buffers();
    auto entry = std::find_if(buffers.begin(), buffers.end(),
                             [buffer](const auto &item) { return item.second == buffer; });
    if (entry == buffers.end()) return;
    const auto &cfg = entry->first->configuration();
    if (cfg.pixelFormat != formats::XRGB8888 && cfg.pixelFormat != formats::ARGB8888 &&
        cfg.pixelFormat != formats::XBGR8888 && cfg.pixelFormat != formats::ABGR8888)
        return;
    if (auraWait_) { --auraWait_; return; }
    if (auraPending_) {
        auraPending_ = false;
        auraFocusState_ = controls::AfStateScanning;
        auraMove(auraFocus_.start(auraFocusPosition_));
        return;
    }
    if (auraCooldown_) { --auraCooldown_; return; }
    if (cfg.size.width < 64 || cfg.size.height < 64 || cfg.stride < cfg.size.width * 4)
        return;
    DmaSyncer sync(buffer->planes()[0].fd, DmaSyncer::SyncType::Read);
    MappedFrameBuffer mapped(buffer, MappedFrameBuffer::MapFlag::Read);
    if (!mapped.isValid() || mapped.planes().empty() ||
        mapped.planes()[0].size() < cfg.stride * cfg.size.height)
        return;
    const auto plane = mapped.planes()[0];
    double edges = 0, mean = 0;
    unsigned int count = 0;
    auto green = [&](unsigned int x, unsigned int y) {
        unsigned int sum = 0;
        for (unsigned int dy = 0; dy < 4; ++dy)
            for (unsigned int dx = 0; dx < 4; ++dx)
                sum += plane[(y + dy) * cfg.stride + (x + dx) * 4 + 1];
        return sum / 16.0;
    };
    for (unsigned int y = cfg.size.height / 3; y < cfg.size.height * 2 / 3; y += 8)
        for (unsigned int x = cfg.size.width / 3; x < cfg.size.width * 2 / 3; x += 8) {
            double value = green(x, y);
            mean += value;
            double dx = value - green(x + 4, y);
            double dy = value - green(x, y + 4);
            edges += dx * dx + dy * dy;
            ++count;
        }
    const double denominator = std::max(mean, count * 8.0);
    const double score = edges * count / (denominator * denominator);
    if (auraFocusState_ == controls::AfStateScanning) {
        auraScoreSum_ += score;
        if (++auraSamples_ < 2) return;
        auto next = auraFocus_.sample(auraScoreSum_ / auraSamples_);
        if (next && !auraMove(*next)) return;
        if (auraFocus_.state() == AuraFocusSearch::State::Focused ||
            auraFocus_.state() == AuraFocusSearch::State::Failed) {
            auraFocusState_ = auraFocus_.state() == AuraFocusSearch::State::Focused ?
                controls::AfStateFocused : controls::AfStateFailed;
            auraReference_ = auraFocus_.score();
            auraCooldown_ = 120;
            auraBadFrames_ = 0;
            LOG(SimplePipeline, Info) << "AURA focus result position=" << auraFocusPosition_
                << " score=" << auraReference_ << " state=" << auraFocusState_;
        }
    } else if (auraFocusMode_ == controls::AfModeContinuous) {
        // Refocus after a sustained contrast loss, not every small fluctuation.
        if (score < auraReference_ * 0.65 || auraFocusState_ == controls::AfStateFailed)
            ++auraBadFrames_;
        else
            auraBadFrames_ = 0;
        if (auraBadFrames_ >= 20) {
            auraPending_ = true;
            auraBadFrames_ = 0;
        }
    }
    metadata.set(controls::AfState, auraFocusState_);
}
'''
new = new.replace(anchor, '\n' + functions + anchor, 1)
anchor = '\tdata->delayedCtrls_->reset();'
assert anchor in new
new = new.replace(anchor, '''    data->auraFocus_.cancel();
    data->auraFocusMode_ = controls::AfModeContinuous;
    data->auraFocusState_ = controls::AfStateIdle;
    data->auraWait_ = 20;
    data->auraCooldown_ = 0;
    data->auraPending_ = true;
    if (controls) data->auraFocusControls(*controls);
''' + anchor, 1)
anchor = 'int SimplePipelineHandler::queueRequestDevice(Camera *camera, Request *request)\n{\n\tSimpleCameraData *data = cameraData(camera);'
assert anchor in new
new = new.replace(anchor, anchor + '\n\tdata->auraFocusControls(request->controls());', 1)
path.write_text(new)
(root / 'port/libcamera-aura-autofocus.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),new.splitlines(True),fromfile='a/src/libcamera/pipeline/simple/simple.cpp',tofile='b/src/libcamera/pipeline/simple/simple.cpp')))
print('Experimental autofocus patch prepared; not installed on phone.')
