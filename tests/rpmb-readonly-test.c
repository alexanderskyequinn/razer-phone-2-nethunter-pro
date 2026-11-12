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
static unsigned opens,calls;
int aura_ufs_parameters(uint32_t *s,uint32_t *l) { *s=32768; *l=64; return 0; }
int __wrap_open(const char *p,int flags,...) {
    assert(!strcmp(p,"/dev/bsg/0:0:0:49476")); assert(flags & O_NOFOLLOW); ++opens; return 10;
}
int __wrap_close(int fd) { assert(fd==10 && opens); --opens; return 0; }
int __wrap_ioctl(int fd,unsigned long cmd,...) {
    va_list args; va_start(args,cmd); struct sg_io_v4 *io=va_arg(args,void *); va_end(args);
    assert(fd==10 && cmd==SG_IO && io->guard=='Q');
    uint8_t *cdb=(void *)(uintptr_t)io->request;
    if(calls==0) assert(cdb[0]==3 && io->din_xfer_len==18 && !io->dout_xfer_len);
    if(calls==1) {
        assert(cdb[0]==0xb5 && cdb[1]==0xec && cdb[3]==1 && io->dout_xfer_len==512);
        uint8_t *f=(void *)(uintptr_t)io->dout_xferp;
        assert(f[510]==0 && f[511]==2); /* Counter query; never key provisioning. */
    }
    if(calls==2) { assert(cdb[0]==0xa2 && io->din_xfer_len==512); memset((void *)(uintptr_t)io->din_xferp,0x42,512); }
    ++calls; return 0;
}
static void put(uint8_t *p,uint32_t x) { for(unsigned i=0;i<4;i++) p[i]=x>>(i*8); }
static uint32_t get(uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void read_request(uint8_t *p) { memset(p,0,20480); put(p,0x102); put(p+4,1); put(p+8,512); put(p+12,24); p[24+511]=2; }
int main(void) {
    uint8_t b[20480]; memset(b,0,sizeof(b)); put(b,0x101); put(b+4,1);
    assert(!aura_rpmb_dispatch(NULL,b,sizeof(b)) && !get(b+8) && get(b+12)==32768 && get(b+16)==64);
    read_request(b); put(b,0x103);
    assert(!aura_rpmb_dispatch(NULL,b,sizeof(b)) && (int32_t)get(b+4)==-EROFS && !calls);
    read_request(b); b[24+511]=1;
    assert(!aura_rpmb_dispatch(NULL,b,sizeof(b)) && (int32_t)get(b+4)==-EINVAL && !calls);
    read_request(b); put(b+12,20479);
    assert(!aura_rpmb_dispatch(NULL,b,sizeof(b)) && (int32_t)get(b+4)==-EINVAL && !calls);
    read_request(b); put(b+4,UINT32_MAX);
    assert(!aura_rpmb_dispatch(NULL,b,sizeof(b)) && (int32_t)get(b+4)==-EINVAL && !calls);
    read_request(b);
    assert(!aura_rpmb_dispatch(NULL,b,sizeof(b)) && !get(b+4) && get(b+8)==512 && b[20]==0x42 && calls==3 && !opens);
    assert(aura_rpmb_dispatch(NULL,b,10)==-1);
    puts("PASS: read-only RPMB dispatch, bounds, prohibited writes/provisioning and counter-query transport");
}
