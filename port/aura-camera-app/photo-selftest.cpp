// SPDX-License-Identifier: GPL-2.0-or-later
#include "aura_photo.h"
#include <vector>
#include <cassert>
int main() {
    AuraPhotoUi photo;
    photo.enabled=true; photo.width=80; photo.height=60; photo.stride=336;
    std::vector<uint8_t> pixels(photo.stride*photo.height,0);
    for (int y=0;y<photo.height;++y) for (int x=0;x<photo.width;++x) {
        uint8_t *p=&pixels[y*photo.stride+x*4];
        p[0]=(x<40 && y<30) || (x>=40 && y>=30) ? 255 : 0;
        p[1]=x>=40 ? 255 : 0;
        p[2]=x<40 && y>=30 ? 255 : 0;
        p[3]=255;
    }
    photo.requested=true;
    photo.save(pixels.data(),pixels.size());
    assert(!photo.requested);
    photo.save(pixels.data(),pixels.size()); // No shutter request: no second file.
    return 0;
}
