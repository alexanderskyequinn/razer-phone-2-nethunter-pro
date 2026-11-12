/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include "../port/aura-fingerprint/aura_fpc_protocol.h"

int main(void)
{
	unsigned char req[64], rsp[64], shared[4096];
	char text[1025];
	/* Independent wire fixture recovered from the stock disassembly. */
	const unsigned char prefix[] = {9,0,0,0,2,0,0,0,255,255,255,255,0,4,0,0};
	aura_fpc_build_info_request(req, rsp, shared);
	assert(!memcmp(shared, prefix, sizeof(prefix)));
	assert(req[0] == 0 && req[1] == 16 && req[2] == 0 && req[3] == 0);
	for (size_t i = 4; i < sizeof(req); ++i)
		assert(req[i] == 0);
	assert(aura_fpc_decode_info(rsp, shared, text, sizeof(text)) == -EIO);
	aura_fpc_put32(rsp, 0);
	assert(aura_fpc_decode_info(rsp, shared, text, sizeof(text)) == -EIO);
	aura_fpc_put32(shared + 8, 0);
	assert(aura_fpc_decode_info(rsp, shared, text, sizeof(text)) == -ENODATA);
	memcpy(shared + 16, "test firmware\nversion 1", 24);
	assert(aura_fpc_decode_info(rsp, shared, text, sizeof(text)) == 0);
	assert(!strcmp(text, "test firmware\nversion 1"));
	assert(aura_fpc_decode_info(rsp, shared, text, 3) == -ENOSPC);
	memset(shared + 16, 'X', 1024);
	assert(aura_fpc_decode_info(rsp, shared, text, sizeof(text)) == -EPROTO);
	shared[1039] = 0;
	assert(aura_fpc_decode_info(rsp, shared, text, sizeof(text)) == 0);
	assert(strlen(text) == 1023);
	aura_fpc_sensor_init_request(req, rsp, shared);
	const unsigned char sensor_prefix[] = {10,0,0,0,4,0,0,0,255,255,255,255};
	assert(!memcmp(shared, sensor_prefix, sizeof(sensor_prefix)));
	for (size_t i = sizeof(sensor_prefix); i < sizeof(shared); ++i)
		assert(!shared[i]);
	assert(aura_fpc_get32(req) == 4096);
	for (size_t i = 4; i < sizeof(req); ++i) assert(!req[i]);
	for (size_t i = 0; i < sizeof(rsp); ++i) assert(rsp[i] == 255);
	aura_fpc_finger_detect_request(req, rsp, shared);
	const unsigned char detect_prefix[] = {10,0,0,0,2,0,0,0,255,255,255,255};
	assert(!memcmp(shared, detect_prefix, sizeof(detect_prefix)));
	for (size_t i = sizeof(detect_prefix); i < sizeof(shared); ++i) assert(!shared[i]);
	aura_fpc_capture_request(req, rsp, shared);
	const unsigned char capture_prefix[] = {10,0,0,0,3,0,0,0,255,255,255,255};
	assert(!memcmp(shared, capture_prefix, sizeof(capture_prefix)));
	for (size_t i = sizeof(capture_prefix); i < sizeof(shared); ++i) assert(!shared[i]);
	puts("FPC wire fixture and bounded reply tests passed");
	return 0;
}
