// SPDX-License-Identifier: GPL-2.0-or-later
#include "aura_photo.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <iostream>
#include <map>
#include <string>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <setjmp.h>
#include <jpeglib.h>

namespace {
struct JpegError { jpeg_error_mgr manager; jmp_buf jump; };
void jpegError(j_common_ptr c) {
    auto *error = reinterpret_cast<JpegError *>(c->err);
    (*c->err->output_message)(c);
    longjmp(error->jump, 1);
}
bool encodePhoto(FILE *file, const uint8_t *data, unsigned char *row,
                 int width, int height, unsigned int stride) {
    jpeg_compress_struct encoder{};
    JpegError error{};
    encoder.err=jpeg_std_error(&error.manager);
    error.manager.error_exit=jpegError;
    if (setjmp(error.jump)) {
        jpeg_destroy_compress(&encoder);
        return false;
    }
    jpeg_create_compress(&encoder);
    jpeg_stdio_dest(&encoder,file);
    encoder.image_width=height;
    encoder.image_height=width;
    encoder.input_components=3;
    encoder.in_color_space=JCS_RGB;
    jpeg_set_defaults(&encoder);
    jpeg_set_quality(&encoder,92,TRUE);
    jpeg_start_compress(&encoder,TRUE);
    while (encoder.next_scanline<encoder.image_height) {
        int sourceX=width-1-encoder.next_scanline;
        for (int x=0; x<height; ++x) {
            const uint8_t *pixel=data+static_cast<size_t>(x)*stride+sourceX*4;
            row[x*3]=pixel[0]; row[x*3+1]=pixel[1]; row[x*3+2]=pixel[2];
        }
        JSAMPROW pointer=row; jpeg_write_scanlines(&encoder,&pointer,1);
    }
    jpeg_finish_compress(&encoder);
    jpeg_destroy_compress(&encoder);
    return true;
}
const std::map<char, std::array<unsigned char,7>> glyphs = {
    {'P',{30,17,17,30,16,16,16}}, {'H',{17,17,17,31,17,17,17}},
    {'O',{14,17,17,17,17,17,14}}, {'T',{31,4,4,4,4,4,4}},
    {'S',{15,16,16,14,1,1,30}}, {'A',{14,17,17,31,17,17,17}},
    {'V',{17,17,17,17,17,10,4}}, {'E',{31,16,16,30,16,16,31}},
    {'D',{30,17,17,17,17,17,30}}, {'R',{30,17,17,30,20,18,17}}
};
void label(SDL_Renderer *r, const char *text, int cx, int y, int scale) {
    int count = std::char_traits<char>::length(text);
    int x = cx - (count*6-1)*scale/2;
    for (int n=0; n<count; ++n) {
        auto it=glyphs.find(text[n]);
        if (it!=glyphs.end()) for (int row=0; row<7; ++row)
            for (int col=0; col<5; ++col) if (it->second[row] & (16>>col)) {
                SDL_Rect pixel{x+col*scale,y+row*scale,scale,scale};
                SDL_RenderFillRect(r,&pixel);
            }
        x+=6*scale;
    }
}
}

void AuraPhotoUi::event(const SDL_Event &e, SDL_Renderer *renderer, SDL_Window *window) {
    if (!enabled) return;
    float x=0, y=0;
    if (e.type==SDL_MOUSEBUTTONUP && e.button.button==SDL_BUTTON_LEFT && e.button.which!=SDL_TOUCH_MOUSEID) {
        SDL_RenderWindowToLogical(renderer,e.button.x,e.button.y,&x,&y);
    } else if (e.type==SDL_FINGERUP) {
        int w,h; SDL_GetWindowSize(window,&w,&h);
        SDL_RenderWindowToLogical(renderer,e.tfinger.x*w,e.tfinger.y*h,&x,&y);
    } else if (e.type==SDL_KEYUP && (e.key.keysym.sym==SDLK_SPACE || e.key.keysym.sym==SDLK_RETURN)) {
        requested=true;
        return;
    } else return;
    if (y>=width && y<width+footer() && x>height/4 && x<height*3/4)
        requested=true;
}

void AuraPhotoUi::save(const uint8_t *data, size_t length) {
    if (!enabled || !requested) return;
    requested=false;
    failed_=true;
    savedAt_=SDL_GetTicks();
    if (!data || width<=0 || height<=0 || stride<static_cast<unsigned>(width)*4 ||
        length<static_cast<size_t>(stride)*height) return;
    const char *home=std::getenv("HOME");
    if (!home) return;
    std::filesystem::path directory=std::filesystem::path(home)/"Pictures"/"Camera";
    std::error_code ec;
    std::filesystem::create_directories(directory,ec);
    if (ec) { std::cerr << "Cannot create photo directory: " << ec.message() << std::endl; return; }
    timespec now{}; clock_gettime(CLOCK_REALTIME,&now);
    tm local{}; localtime_r(&now.tv_sec,&local);
    char date[40]; strftime(date,sizeof(date),"IMG_%Y%m%d_%H%M%S",&local);
    std::string filename=(directory/(std::string(date)+"_"+std::to_string(now.tv_nsec)+".jpg")).string();
    int fd=open(filename.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
    if (fd<0) return;
    FILE *file=fdopen(fd,"wb");
    if (!file) { close(fd); unlink(filename.c_str()); return; }
    // Keep all owning C++ objects outside the libjpeg setjmp boundary.
    std::vector<unsigned char> row(static_cast<size_t>(height)*3);
    bool ok=encodePhoto(file,data,row.data(),width,height,stride);
    if (fflush(file)!=0) ok=false;
    if (ok) ok=fsync(fileno(file))==0;
    if (fclose(file)!=0) ok=false;
    if (!ok) { unlink(filename.c_str()); return; }
    failed_=false;
    std::cout << "AURA_PHOTO_SAVED " << filename << " " << height << "x" << width << std::endl;
}

void AuraPhotoUi::draw(SDL_Renderer *renderer) {
    if (!enabled) return;
    SDL_Rect bar{0,width,height,footer()};
    SDL_SetRenderDrawColor(renderer,18,21,26,255);
    SDL_RenderFillRect(renderer,&bar);
    int radius=footer()/4, cx=height/2, cy=width+footer()/3;
    SDL_SetRenderDrawColor(renderer,245,247,250,255);
    for (int y=-radius; y<=radius; ++y) {
        int x=std::sqrt(radius*radius-y*y);
        SDL_RenderDrawLine(renderer,cx-x,cy+y,cx+x,cy+y);
    }
    bool recent=savedAt_ && SDL_GetTicks()-savedAt_<2500;
    if (recent) SDL_SetRenderDrawColor(renderer,failed_?255:80,failed_?95:220,failed_?95:155,255);
    label(renderer,recent?(failed_?"ERROR":"SAVED"):"PHOTO",cx,width+footer()*2/3,std::max(1,footer()/30));
}
