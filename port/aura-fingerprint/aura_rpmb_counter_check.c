/* SPDX-License-Identifier: MIT
 * Public write-counter protocol health check, no protected-record read.
 */
#include "aura_rpmb_readonly.c"
#include <sys/random.h>
int main(void)
{
    uint8_t buffer[20480]={0},nonce[16];
    if(getrandom(nonce,sizeof(nonce),0)!=sizeof(nonce)) return 1;
    put32(buffer,0x102); put32(buffer+4,1); put32(buffer+8,512); put32(buffer+12,24);
    buffer[24+511]=2; memcpy(buffer+24+484,nonce,16);
    if(aura_rpmb_dispatch(NULL,buffer,sizeof(buffer)) || le32(buffer+4) || le32(buffer+8)!=512) {
        fprintf(stderr,"RPMB counter transport failed, status=%d\n",(int32_t)le32(buffer+4)); return 1;
    }
    uint8_t *reply=buffer+20;
    unsigned type=(unsigned)reply[510]<<8|reply[511],status=(unsigned)reply[508]<<8|reply[509];
    int nonce_ok=!memcmp(nonce,reply+484,16);
    printf("Counter response type=0x%x status=%u nonce_matches=%s; counter/MAC not logged.\n",type,status,nonce_ok ? "yes" : "no");
    explicit_bzero(buffer,sizeof(buffer)); explicit_bzero(nonce,sizeof(nonce));
    return type==0x200 && !status && nonce_ok ? 0 : 1;
}
