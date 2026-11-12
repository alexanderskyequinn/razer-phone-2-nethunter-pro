// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <SDL2/SDL.h>
#include <cstddef>
#include <cstdint>

class AuraPhotoUi {
public:
    bool enabled = false;
    bool requested = false;
    unsigned int stride = 0;
    int width = 0, height = 0;
    int footer() const { return enabled ? height / 5 : 0; }
    void event(const SDL_Event &event, SDL_Renderer *renderer, SDL_Window *window);
    void save(const uint8_t *data, size_t length);
    void draw(SDL_Renderer *renderer);
private:
    Uint32 savedAt_ = 0;
    bool failed_ = false;
};
