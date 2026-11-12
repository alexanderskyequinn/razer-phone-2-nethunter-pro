/* SPDX-License-Identifier: BSD-3-Clause-Clear
 * Read-only UFS descriptor query, based on Qualcomm minkipc rpmb_ufs.c.
 * No SECURITY PROTOCOL command, protected-record read, write or key provision.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <endian.h>
#include <linux/bsg.h>
#include <scsi/sg.h>
#include <scsi/scsi_bsg_ufs.h>

static int descriptor(int fd, uint8_t id, uint8_t index, uint8_t *data, uint16_t size)
{
    struct ufs_bsg_request request = {0};
    struct ufs_bsg_reply reply = {0};
    struct sg_io_v4 io = {0};
    request.msgcode = 0x16; /* UTP_UPIU_QUERY_REQ */
    request.upiu_req.header.dword_0 = htobe32(0x16000000);
    request.upiu_req.header.dword_1 = htobe32(0x00010000); /* standard read */
    request.upiu_req.header.dword_2 = htobe32(size);
    request.upiu_req.qr.opcode = 1; /* READ_DESC only */
    request.upiu_req.qr.idn = id;
    request.upiu_req.qr.index = index;
    request.upiu_req.qr.length = htobe16(size);
    io.guard = 'Q';
    io.protocol = BSG_PROTOCOL_SCSI;
    io.subprotocol = BSG_SUB_PROTOCOL_SCSI_TRANSPORT;
    io.request_len = sizeof(request);
    io.request = (uintptr_t)&request;
    io.max_response_len = sizeof(reply);
    io.response = (uintptr_t)&reply;
    io.din_xfer_len = size;
    io.din_xferp = (uintptr_t)data;
    io.timeout = 5000;
    if (ioctl(fd, SG_IO, &io)) return -1;
    if (io.info || io.device_status || io.transport_status || io.driver_status || reply.result ||
        io.din_resid || data[1] != id || data[0] < size) { errno=EPROTO; return -1; }
    return 0;
}

int aura_ufs_parameters(uint32_t *sectors_out, uint32_t *frames_out)
{
    uint8_t device[0x40]={0}, geometry[0x48]={0}, unit[0x23]={0};
    int fd=open("/dev/bsg/ufs-bsg0",O_RDWR|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0) { perror("Open UFS query interface"); return 1; }
    int result=descriptor(fd,0,0,device,sizeof(device)) ||
               descriptor(fd,7,0,geometry,sizeof(geometry)) ||
               descriptor(fd,2,0xc4,unit,sizeof(unit));
    if(result) perror("Read public UFS descriptor");
    else {
        uint16_t version=(uint16_t)device[16]<<8|device[17];
        uint32_t blocks=(uint32_t)unit[15]<<24|(uint32_t)unit[16]<<16|(uint32_t)unit[17]<<8|unit[18];
        uint32_t sectors=version<0x300 ? blocks/2 : (uint32_t)unit[19]*256;
        if(!sectors || !geometry[23]) result=1;
        else { *sectors_out=sectors; *frames_out=geometry[23]; }
    }
    if(close(fd)) result=1;
    return result ? 1 : 0;
}

#ifndef AURA_UFS_LIBRARY
int main(void)
{
    uint32_t sectors=0,frames=0;
    int result=aura_ufs_parameters(&sectors,&frames);
    if(!result) printf("RPMB sectors(512-byte)=%u transfer_limit_frames=%u\n",sectors,frames);
    return result;
}
#endif
