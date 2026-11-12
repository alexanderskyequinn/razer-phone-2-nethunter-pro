/* SPDX-License-Identifier: MIT */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/bsg.h>
#include <scsi/sg.h>
#include <stdarg.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include "qsee_supplicant.h"
int aura_rpmb_dispatch(struct qs_store *,void *,size_t);
static unsigned opens,calls,limit=64,expected_frames=2;
static int fail_at=-1,fail_kind;
static uint8_t expected[1024];
int aura_ufs_parameters(uint32_t *s,uint32_t *l) { *s=32768; *l=limit; return 0; }
int __wrap_open(const char *p,int flags,...) {
    assert(!strcmp(p,"/dev/bsg/0:0:0:49476")); assert(flags & O_NOFOLLOW); ++opens; return 10;
}
int __wrap_close(int fd) { assert(fd==10 && opens); --opens; return 0; }
int __wrap_ioctl(int fd,unsigned long cmd,...) {
    va_list args; va_start(args,cmd); struct sg_io_v4 *io=va_arg(args,void *); va_end(args);
    assert(fd==10 && cmd==SG_IO && io->guard=='Q' && io->timeout==5000);
    uint8_t *cdb=(void *)(uintptr_t)io->request;
    unsigned step=calls++;
    if(step==0) assert(cdb[0]==3 && io->din_xfer_len==18 && !io->dout_xfer_len);
    if(step==1) {
        assert(cdb[0]==0xb5 && cdb[1]==0xec && cdb[3]==1 && io->dout_xfer_len==expected_frames*512);
        assert(!memcmp((void *)(uintptr_t)io->dout_xferp,expected,expected_frames*512));
    }
    if(step==2) {
        uint8_t result_request[512]={0}; result_request[511]=5;
        assert(cdb[0]==0xb5 && io->dout_xfer_len==512);
        assert(!memcmp((void *)(uintptr_t)io->dout_xferp,result_request,512));
    }
    if(step==3) {
        assert(cdb[0]==0xa2 && io->din_xfer_len==512);
        /* Deliberately nonzero device result: must be forwarded, not hidden. */
        memset((void *)(uintptr_t)io->din_xferp,0x42,512);
    }
    assert(step<=3);
    if((int)step==fail_at) {
        if(fail_kind==0) { errno=EIO; return -1; }
        if(fail_kind==1) io->device_status=2;
        if(fail_kind==2) { if(io->dout_xfer_len) io->dout_resid=1; else io->din_resid=1; }
    }
    return 0;
}
static void put(uint8_t *p,uint32_t x) { for(unsigned i=0;i<4;i++) p[i]=x>>(i*8); }
static uint32_t get(uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void request(uint8_t *p) {
    memset(p,0,20480); put(p,0x103); put(p+4,2); put(p+8,1024); put(p+12,24); put(p+16,1); put(p+20,2);
    for(unsigned i=0;i<2;i++) {
        uint8_t *f=p+24+i*512;
        memset(f+196,0x81+i,32); memset(f+228,0x21+i,256);
        f[503]=7; f[505]=32; f[507]=2; f[511]=3;
    }
    memcpy(expected,p+24,1024); calls=0; fail_at=-1; limit=64; expected_frames=2;
}
static void rejected(uint8_t *b) {
    assert(!aura_rpmb_dispatch(NULL,b,20480));
    assert((int32_t)get(b+4)==-EINVAL && !get(b+8) && !calls && !opens);
}
int main(void) {
    uint8_t b[20480];
    request(b); assert(!aura_rpmb_dispatch(NULL,b,sizeof(b)));
    assert(!get(b+4) && get(b+8)==512 && get(b+12)==20 && get(b+16)==1 && b[20]==0x42 && calls==4 && !opens);
    request(b); put(b+4,1); put(b+8,512); put(b+20,1); b[24+507]=1;
    memcpy(expected,b+24,512); expected_frames=1;
    assert(!aura_rpmb_dispatch(NULL,b,sizeof(b)) && !get(b+4) && calls==4 && !opens);
    request(b); b[24+511]=1; rejected(b); /* irreversible key provision prohibited */
    request(b); b[24+512+511]=1; rejected(b); /* also inside a batch */
    request(b); put(b+20,1); rejected(b); /* don't split MAC transaction */
    request(b); put(b+20,0); rejected(b);
    request(b); b[24+512+503]++; rejected(b); /* inconsistent counter */
    request(b); b[24+512+505]++; rejected(b); /* inconsistent address */
    request(b); b[24+512+507]=1; rejected(b); /* inconsistent count */
    request(b); limit=1; rejected(b);
    request(b); b[24+504]=255; b[24+505]=255; rejected(b); /* capacity overrun */
    request(b); put(b+12,20479); rejected(b);
    request(b); put(b+12,20); rejected(b);
    request(b); put(b+8,512); rejected(b);
    request(b); put(b+4,UINT32_MAX); rejected(b);
    request(b); put(b+4,0); rejected(b);
    for(int kind=0;kind<3;kind++) for(int step=0;step<4;step++) {
        request(b); fail_at=step; fail_kind=kind;
        assert(!aura_rpmb_dispatch(NULL,b,sizeof(b)));
        assert((int32_t)get(b+4)==-EIO && !get(b+8) && calls==(unsigned)step+1 && !opens);
        for(unsigned i=20;i<sizeof(b);i++) assert(!b[i]);
    }
    puts("PASS: authenticated writes preserve frames, prohibit key provisioning, validate bounds and fail without retries at every transport stage");
}
