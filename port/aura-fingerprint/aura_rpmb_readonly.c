/* SPDX-License-Identifier: BSD-3-Clause-Clear
 * Qualcomm MinkIPC RPMB wire format adapted to the legacy QSEE transport.
 * Default build is read-only. AURA_RPMB_AUTHENTICATED_WRITE enables only
 * pre-authenticated type-3 frames supplied by secure firmware. Key programming
 * remains prohibited. No key generation, payload logging or write retries.
 */
#define _GNU_SOURCE
#include "qsee_supplicant.h"
#include <errno.h>
#include <fcntl.h>
#include <linux/bsg.h>
#include <scsi/sg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

int aura_ufs_parameters(uint32_t *sectors, uint32_t *frames);
static uint32_t le32(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void put32(uint8_t *p,uint32_t v) { for(unsigned i=0;i<4;i++) p[i]=v>>(8*i); }

static int scsi(int fd, uint8_t *cdb, unsigned cdb_size, void *data, unsigned size, int output)
{
    uint8_t sense[96]={0};
    struct sg_io_v4 io={0};
    io.guard='Q'; io.protocol=BSG_PROTOCOL_SCSI; io.subprotocol=BSG_SUB_PROTOCOL_SCSI_CMD;
    io.request_len=cdb_size; io.request=(uintptr_t)cdb;
    io.response=(uintptr_t)sense; io.max_response_len=sizeof(sense); io.timeout=5000;
    if(output) { io.dout_xfer_len=size; io.dout_xferp=(uintptr_t)data; }
    else { io.din_xfer_len=size; io.din_xferp=(uintptr_t)data; }
    if(ioctl(fd,SG_IO,&io)) return -errno;
    if(io.info || io.device_status || io.transport_status || io.driver_status ||
       (output ? io.dout_resid : io.din_resid)) return -EIO;
    return 0;
}

static void command(uint8_t cdb[12], uint8_t opcode, uint32_t bytes)
{
    memset(cdb,0,12); cdb[0]=opcode; cdb[1]=0xec; cdb[3]=1;
    cdb[6]=bytes>>24; cdb[7]=bytes>>16; cdb[8]=bytes>>8; cdb[9]=bytes;
}

#ifdef AURA_RPMB_AUTHENTICATED_WRITE
static unsigned be16(const uint8_t *p) { return (unsigned)p[0]<<8|p[1]; }

static int write_frames(const uint8_t *request, uint32_t frames, uint32_t batch,
                        uint8_t response[512])
{
    uint32_t sectors=0,limit=0;
    if(aura_ufs_parameters(&sectors,&limit)) return -ENODEV;
    /* Accept one complete firmware-authenticated transaction. Never split its
     * MAC across transactions, silently truncate frames or retry a write. */
    if(!frames || batch!=frames || frames>limit) return -EINVAL;
    unsigned address=be16(request+504);
    if((uint64_t)address+frames > (uint64_t)sectors*2) return -EINVAL;
    for(uint32_t i=0;i<frames;i++) {
        const uint8_t *f=request+i*512;
        if(be16(f+510)!=3 || be16(f+506)!=frames ||
           be16(f+504)!=address || memcmp(f+500,request+500,4)) return -EINVAL;
    }
    int fd=open("/dev/bsg/0:0:0:49476",O_RDWR|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0) return -errno;
    uint8_t cdb[12],sense_request[6]={3,0,0,0,18,0},sense[18]={0};
    uint8_t result_request[512]={0}; result_request[511]=5;
    int result=scsi(fd,sense_request,6,sense,sizeof(sense),0);
    if(!result) {
        command(cdb,0xb5,frames*512);
        result=scsi(fd,cdb,12,(void *)request,frames*512,1);
    }
    if(!result) {
        command(cdb,0xb5,512);
        result=scsi(fd,cdb,12,result_request,512,1);
    }
    if(!result) {
        command(cdb,0xa2,512);
        result=scsi(fd,cdb,12,response,512,0);
    }
    /* Forward the authenticated device result to secure firmware unchanged;
     * it checks the MAC, counter and result. A transport success is not an
     * enrollment success. An ambiguous transport failure is never replayed. */
    if(close(fd) && !result) result=-errno;
    explicit_bzero(result_request,sizeof(result_request));
    return result;
}
#endif

static int read_frames(const uint8_t request[512], uint32_t frames, uint8_t *response)
{
    uint32_t sectors=0,limit=0;
    if(aura_ufs_parameters(&sectors,&limit) || frames>limit) return -ENODEV;
    unsigned type=(unsigned)request[510]<<8|request[511];
    unsigned address=(unsigned)request[504]<<8|request[505];
    if(type==4 && ((uint64_t)address+frames > (uint64_t)sectors*2)) return -EINVAL;
    int fd=open("/dev/bsg/0:0:0:49476",O_RDWR|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0) return -errno;
    uint8_t cdb[12],sense_request[6]={3,0,0,0,18,0},sense[18]={0};
    int result=scsi(fd,sense_request,6,sense,sizeof(sense),0);
    if(!result) {
        command(cdb,0xb5,512);
        result=scsi(fd,cdb,12,(void *)request,512,1);
    }
    if(!result) {
        command(cdb,0xa2,frames*512);
        result=scsi(fd,cdb,12,response,frames*512,0);
    }
    if(close(fd) && !result) result=-errno;
    return result;
}

int aura_rpmb_dispatch(struct qs_store *store, void *buffer, size_t size)
{
    (void)store;
    uint8_t *p=buffer;
    if(size<24) return -1;
    uint32_t cmd=le32(p),version=le32(p+4),count=0,bytes=0,offset=0;
    int status=-EINVAL;
    if(cmd==0x101) {
        uint32_t sectors=0,limit=0;
        status=aura_ufs_parameters(&sectors,&limit) ? -ENODEV : 0;
        memset(p,0,size); put32(p,cmd); put32(p+4,version); put32(p+8,status);
        if(!status) { put32(p+12,sectors); put32(p+16,limit); }
    } else if(cmd==0x102 || cmd==0x103) {
        count=le32(p+4); bytes=le32(p+8); offset=le32(p+12); version=le32(p+16);
        uint8_t request[20480]={0};
        uint32_t response_frames=count;
        int valid=cmd==0x102 && count>0 && count<=(size-20)/512 && bytes==512 &&
                  offset>=24 && offset<=size && bytes<=size-offset;
        if(valid) {
            memcpy(request,p+offset,512);
            unsigned type=(unsigned)request[510]<<8|request[511];
            unsigned blocks=(unsigned)request[506]<<8|request[507];
            valid=(type==2 && count==1) || (type==4 && (!blocks || blocks==count));
        }
#ifdef AURA_RPMB_AUTHENTICATED_WRITE
        uint32_t batch=le32(p+20);
        if(cmd==0x103) {
            valid=count>0 && count<=sizeof(request)/512 &&
                  bytes==count*512 && offset>=24 && offset<=size && bytes<=size-offset;
            if(valid) memcpy(request,p+offset,bytes);
            response_frames=1;
        }
#endif
        memset(p,0,size);
#ifdef AURA_RPMB_AUTHENTICATED_WRITE
        status=!valid ? -EINVAL : cmd==0x103 ? write_frames(request,count,batch,p+20) :
                read_frames(request,count,p+20);
#else
        status=cmd==0x103 ? -EROFS : valid ? read_frames(request,count,p+20) : -EINVAL;
#endif
        explicit_bzero(request,sizeof(request));
        if(status) memset(p+20,0,size-20);
        put32(p,cmd); put32(p+4,status); put32(p+8,status ? 0 : response_frames*512);
        put32(p+12,20); put32(p+16,version);
    } else if(cmd==0x104) {
        memset(p,0,size); put32(p,cmd); put32(p+4,(uint32_t)-1); put32(p+12,16);
        status=-1; /* Match documented unsupported partition-table response. */
    } else return -1;
    fprintf(stderr,"RPMB diagnostic command=0x%x status=%d frames=%u; no payload logged\n",cmd,status,count);
    return 0;
}
