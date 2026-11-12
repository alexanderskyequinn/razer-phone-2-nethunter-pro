"""Apply the Razer preview's user-verified portrait correction to SDL output."""
from pathlib import Path
import difflib
root = Path(__file__).resolve().parents[1]
source = Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa')
p = source/'src/apps/cam/sdl_sink.cpp'
original = p.read_text()
if 'AURA_CAMERA_PORTRAIT' not in original:
    new = original.replace('#include <assert.h>', '#include <assert.h>\n#include <cstdlib>')
    old = '\tinit_ = true;\n\twindow_'
    replacement = '\tinit_ = true;\n\tconst bool portrait = std::getenv("AURA_CAMERA_PORTRAIT") != nullptr;\n\tconst int width = portrait ? rect_.h : rect_.w;\n\tconst int height = portrait ? rect_.w : rect_.h;\n\twindow_'
    assert old in new
    new = new.replace(old, replacement, 1)
    assert 'SDL_WINDOWPOS_UNDEFINED, rect_.w,\n\t\t\t\t   rect_.h,' in new
    new = new.replace('SDL_WINDOWPOS_UNDEFINED, rect_.w,\n\t\t\t\t   rect_.h,', 'SDL_WINDOWPOS_UNDEFINED, width,\n\t\t\t\t   height,', 1)
    new = new.replace('SDL_RenderSetLogicalSize(renderer_, rect_.w, rect_.h)', 'SDL_RenderSetLogicalSize(renderer_, width, height)', 1)
    old = '\tSDL_RenderCopy(renderer_, texture_->get(), nullptr, nullptr);'
    assert old in new
    new = new.replace(old, '''\tif (std::getenv("AURA_CAMERA_PORTRAIT")) {
\t\t/* The user verified that the sensor image is 90 degrees clockwise.
\t\t * Rotate only presentation, keeping the capture pixels untouched. */
\t\tSDL_Rect dst{ (rect_.h - rect_.w) / 2,
\t\t\t      (rect_.w - rect_.h) / 2, rect_.w, rect_.h };
\t\tSDL_RenderCopyEx(renderer_, texture_->get(), nullptr, &dst,
\t\t\t\t -90.0, nullptr, SDL_FLIP_NONE);
\t} else {
\t\tSDL_RenderCopy(renderer_, texture_->get(), nullptr, nullptr);
\t}''', 1)
    p.write_text(new)
    (root/'port/libcamera-aura-preview.patch').write_bytes(''.join(difflib.unified_diff(original.splitlines(True), new.splitlines(True), fromfile='a/src/apps/cam/sdl_sink.cpp', tofile='b/src/apps/cam/sdl_sink.cpp')).encode())
