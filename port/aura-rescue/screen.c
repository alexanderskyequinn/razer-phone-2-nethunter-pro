/* RAM recovery display. Uses bounded fb writes, bypassing broken fbcon blits. */
#include <errno.h>
#include <fcntl.h>
#include <glob.h>
#include <linux/fb.h>
#include <linux/input.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <unistd.h>

static const unsigned char glyph[][7] = {
 {14,17,17,31,17,17,17},{30,17,17,30,17,17,30},{14,17,16,16,16,17,14},
 {30,17,17,17,17,17,30},{31,16,16,30,16,16,31},{31,16,16,30,16,16,16},
 {14,17,16,23,17,17,15},{17,17,17,31,17,17,17},{31,4,4,4,4,4,31},
 {7,2,2,2,18,18,12},{17,18,20,24,20,18,17},{16,16,16,16,16,16,31},
 {17,27,21,21,17,17,17},{17,25,21,19,17,17,17},{14,17,17,17,17,17,14},
 {30,17,17,30,16,16,16},{14,17,17,17,21,18,13},{30,17,17,30,20,18,17},
 {15,16,16,14,1,1,30},{31,4,4,4,4,4,4},{17,17,17,17,17,17,14},
 {17,17,17,17,17,10,4},{17,17,17,21,21,21,10},{17,17,10,4,10,17,17},
 {17,17,10,4,4,4,4},{31,1,2,4,8,16,31},
 {14,17,19,21,25,17,14},{4,12,4,4,4,4,14},{14,17,1,2,4,8,31},
 {30,1,1,14,1,1,30},{2,6,10,18,31,2,2},{31,16,16,30,1,1,30},
 {14,16,16,30,17,17,14},{31,1,2,4,8,8,8},{14,17,17,14,17,17,14},
 {14,17,17,15,1,1,14}
};
static struct fb_var_screeninfo v;
static struct fb_fix_screeninfo f;
static unsigned char *pixels;
static unsigned selection;
static uint32_t field(unsigned c, struct fb_bitfield b) {
 return b.length ? (c >> (8-b.length)) << b.offset : 0;
}
static uint32_t color(unsigned rgb) {
 return field(rgb>>16,v.red)|field((rgb>>8)&255,v.green)|field(rgb&255,v.blue)|field(255,v.transp);
}
static void rect(unsigned x,unsigned y,unsigned w,unsigned h,unsigned rgb) {
 uint32_t c=color(rgb);
 for(unsigned yy=y; yy<y+h && yy<v.yres; ++yy)
  for(unsigned xx=x; xx<x+w && xx<v.xres; ++xx)
   *(uint32_t *)(pixels+(size_t)yy*f.line_length+xx*4)=c;
}
static void text(unsigned y,const char *s,unsigned scale,unsigned rgb) {
 unsigned x=90;
 for(;*s;++s,x+=6*scale) {
  int n=*s>='A'&&*s<='Z'?*s-'A':*s>='0'&&*s<='9'?26+*s-'0':-1;
  if(n>=0) for(unsigned r=0;r<7;++r) for(unsigned c=0;c<5;++c)
   if(glyph[n][r]&(16>>c)) rect(x+c*scale,y+r*scale,scale,scale,rgb);
  if(*s=='.') rect(x+2*scale,y+6*scale,scale,scale,rgb);
 }
}
static int draw(int fd,size_t size) {
 rect(70,1930,1300,600,0x101b29);
 const char *items[]={"START KALI","DOWNLOAD MODE","POWER OFF"};
 for(unsigned n=0;n<3;++n)text(1960+n*110,items[n],9,n==selection?0x46cdb8:0xa4b7ca);
 text(2360,"VOLUME TO SELECT",8,0xffffff);
 text(2460,"POWER TO CONFIRM",8,0xffffff);
 for(size_t done=0;done<size;) {
  ssize_t n=pwrite(fd,pixels+done,size-done,done);
  if(n<0&&errno==EINTR)continue;
  if(n<=0){perror("framebuffer write");return 5;}done+=n;
 }
 return 0;
}
int main(void) {
 setbuf(stdout,NULL);
 int fd=-1;
 for(int n=0;n<40 && fd<0;++n) {fd=open("/dev/fb0",O_RDWR);if(fd<0)sleep(1);}
 if(fd<0) {perror("fb0");return 1;}
 if(ioctl(fd,FBIOGET_VSCREENINFO,&v)||ioctl(fd,FBIOGET_FSCREENINFO,&f))return 2;
 if(v.xres!=1440||v.yres!=2560||v.bits_per_pixel!=32||v.xoffset||v.yoffset||
    f.visual!=FB_VISUAL_TRUECOLOR||f.line_length<5760||f.line_length>32768||
    (uint64_t)f.line_length*v.yres>f.smem_len||v.red.length>8||v.green.length>8||
    v.blue.length>8||v.transp.length>8||v.red.offset+v.red.length>32||
    v.green.offset+v.green.length>32||v.blue.offset+v.blue.length>32||
    v.transp.offset+v.transp.length>32) return 3;
 size_t size=(size_t)f.line_length*v.yres;
 pixels=calloc(1,size);if(!pixels)return 4;
 rect(0,0,1440,2560,0x101b29);rect(90,210,1260,12,0x46cdb8);
 text(300,"AURA",22,0xffffff);text(500,"RECOVERY",18,0xffffff);
 text(800,"RUNNING FROM RAM",10,0x46cdb8);
 text(980,"KALI STORAGE IS",9,0xffffff);
 text(1090,"NOT MOUNTED",9,0xffffff);
 if(access("/etc/aura-rescue-remote-enabled",F_OK)==0) {
  text(1350,"CONNECT USB TO PC",10,0xffffff);
  text(1540,"SSH 192.0.2.1",11,0x46cdb8);
  text(1690,"KEY LOGIN ONLY",9,0xffffff);
 } else {
  text(1350,"LOCAL RECOVERY",10,0xffffff);
  text(1540,"REMOTE ACCESS OFF",10,0x46cdb8);
  text(1690,"NO PC KEY NEEDED",9,0xffffff);
 }
 if(draw(fd,size))return 5;
 puts("Recovery framebuffer screen written");
 glob_t paths={0};struct pollfd keys[8];unsigned count=0;
 if(!glob("/dev/input/event*",0,NULL,&paths))for(size_t n=0;n<paths.gl_pathc&&count<8;++n){
  int input=open(paths.gl_pathv[n],O_RDONLY|O_NONBLOCK);char name[128]={0};
  if(input<0)continue;
  if(ioctl(input,EVIOCGNAME(sizeof(name)),name)>=0&&
     (strstr(name,"gpio-keys")||strstr(name,"pwrkey")))
   keys[count++]=(struct pollfd){.fd=input,.events=POLLIN};
  else close(input);
 }
 globfree(&paths);printf("Recovery button devices: %u\n",count);
 while(count){
  if(poll(keys,count,-1)<0){if(errno==EINTR)continue;break;}
  for(unsigned n=0;n<count;++n)if(keys[n].revents&POLLIN){
   struct input_event e;
   while(read(keys[n].fd,&e,sizeof(e))==sizeof(e)){
    if(e.type!=EV_KEY||e.value!=1)continue;
    if(e.code==KEY_VOLUMEUP){selection=(selection+2)%3;draw(fd,size);}
    if(e.code==KEY_VOLUMEDOWN){selection=(selection+1)%3;draw(fd,size);}
    if(e.code==KEY_POWER){
     const char *action[]={"boot-kali","bootloader","poweroff"};
     pid_t child=fork();
     if(child==0){execl("/bin/aura-rescue","aura-rescue",action[selection],(char *)NULL);_exit(127);}
     if(child>0){int status;waitpid(child,&status,0);printf("Recovery action returned %d\n",status);}
    }
   }
  }
 }
 free(pixels);close(fd);return 0;
}
