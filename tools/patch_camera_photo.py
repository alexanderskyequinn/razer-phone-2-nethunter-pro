"""Add an opt-in touch shutter to the known working SDL preview."""
from pathlib import Path
import difflib
import shutil
root=Path(__file__).resolve().parents[1]
source=Path('/var/tmp/aura-kali-rootfs/var/tmp/aura-libcamera-work/libcamera-v0.7.2-191e202178f02430b5942397c70d215cdd2056fa/src/apps/cam')
for name in ('aura_photo.h','aura_photo.cpp'):
    shutil.copyfile(root/'port/aura-camera-app'/name,source/name)
changes=[]
def patch(name, edits):
    p=source/name; old=p.read_text(); new=old
    for before,after in edits:
        if after in new: continue
        assert before in new,(name,before)
        new=new.replace(before,after,1)
    if new != old: p.write_text(new)
    changes.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/src/apps/cam/'+name,tofile='b/src/apps/cam/'+name))
patch('meson.build',[("'sdl_sink.cpp',","'sdl_sink.cpp',\n        'aura_photo.cpp',")])
patch('sdl_sink.h',[('#include "frame_sink.h"','#include "frame_sink.h"\n#include "aura_photo.h"'),('SDL_Window *window_;','AuraPhotoUi photo_;\n\tSDL_Window *window_;')])
patch('sdl_sink.cpp',[
    ('rect_.h = cfg.size.height;','rect_.h = cfg.size.height;\n\tphoto_.enabled = std::getenv("AURA_CAMERA_PHOTOS") && cfg.pixelFormat == formats::ABGR8888;\n\tphoto_.width = rect_.w; photo_.height = rect_.h; photo_.stride = cfg.stride;'),
    ('const int height = portrait ? rect_.w : rect_.h;','const int height = (portrait ? rect_.w : rect_.h) + photo_.footer();'),
    ('SDL_CreateWindow("",','SDL_CreateWindow(photo_.enabled ? "Rear Camera" : "Rear Camera Preview",'),
    ('renderer_ = SDL_CreateRenderer(window_, -1, 0);','SDL_StopTextInput(); // Camera has no text fields; keep the on-screen keyboard hidden.\n\trenderer_ = SDL_CreateRenderer(window_, -1, 0);'),
    ('for (SDL_Event e; SDL_PollEvent(&e);) {','for (SDL_Event e; SDL_PollEvent(&e);) {\n\t\tphoto_.event(e, renderer_, window_);'),
    ('photo_.event(e, renderer_, window_);','photo_.event(e, renderer_, window_);\n\t\tif (e.type == SDL_WINDOWEVENT && e.window.event == SDL_WINDOWEVENT_FOCUS_GAINED)\n\t\t\tSDL_StopTextInput();'),
    ('texture_->update(planes);','texture_->update(planes);\n\tif (!planes.empty()) photo_.save(planes[0].data(), planes[0].size());'),
    ('SDL_RenderPresent(renderer_);','photo_.draw(renderer_);\n\tSDL_RenderPresent(renderer_);'),
])
if changes:
    (root/'port/libcamera-aura-photo.patch').write_bytes(''.join(changes).encode())
