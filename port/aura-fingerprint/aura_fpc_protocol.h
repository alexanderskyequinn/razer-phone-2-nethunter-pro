/* SPDX-License-Identifier: MIT */
#ifndef AURA_FPC_PROTOCOL_H
#define AURA_FPC_PROTOCOL_H
#include <errno.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>

/* Stock HAL: fpc_tee_print_build_info at 0x54a8, constant at 0x7fd0;
 * fpc_tac_transfer at 0x6e38. The 1040-byte request is page-rounded by ION.
 * Explicit sensor test commands are defined below. No enrollment, matching,
 * template access, or image-export command is implemented here.
 */
#define AURA_FPC_SHARED_SIZE 4096u
#define AURA_FPC_XFER_SIZE 64u
#define AURA_FPC_INFO_SIZE 1024u
#define AURA_FPC_ADDRESS_OFFSET 4u

static inline void aura_fpc_put32(void *where, uint32_t value)
{
	unsigned char *p = where;
	p[0] = value;
	p[1] = value >> 8;
	p[2] = value >> 16;
	p[3] = value >> 24;
}

static inline uint32_t aura_fpc_get32(const void *where)
{
	const unsigned char *p = where;
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
	       ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static inline void aura_fpc_build_info_request(unsigned char *request,
					     unsigned char *response,
					     unsigned char *shared)
{
	memset(request, 0, AURA_FPC_XFER_SIZE);
	memset(response, 0xff, AURA_FPC_XFER_SIZE);
	memset(shared, 0, AURA_FPC_SHARED_SIZE);
	aura_fpc_put32(request, AURA_FPC_SHARED_SIZE);
	/* request+4 remains zero until the kernel patches a checked TZ address. */
	aura_fpc_put32(shared, 9);
	aura_fpc_put32(shared + 4, 2);
	aura_fpc_put32(shared + 8, UINT32_MAX);
	aura_fpc_put32(shared + 12, AURA_FPC_INFO_SIZE);
}

static inline int aura_fpc_decode_info(const unsigned char *response,
				       const unsigned char *shared,
				       char *text, size_t capacity)
{
	const unsigned char *end;
	size_t len;

	if (aura_fpc_get32(response) || aura_fpc_get32(shared + 8))
		return -EIO;
	end = memchr(shared + 16, 0, AURA_FPC_INFO_SIZE);
	if (!end)
		return -EPROTO;
	len = (size_t)(end - (shared + 16));
	if (!len)
		return -ENODATA;
	if (capacity <= len)
		return -ENOSPC;
	memcpy(text, shared + 16, len);
	text[len] = 0;
	return 0;
}

/* Stock fpc_tee_sensor_init at 0x5c78 calls the helper at 0x56d4 with
 * subcommand 4. It writes [10, 4, status] to the same page-rounded buffer.
 * The same command is used at release. This does not capture a fingerprint.
 */
static inline void aura_fpc_sensor_init_request(unsigned char *request,
					      unsigned char *response,
					      unsigned char *shared)
{
	memset(request, 0, AURA_FPC_XFER_SIZE);
	memset(response, 0xff, AURA_FPC_XFER_SIZE);
	memset(shared, 0, AURA_FPC_SHARED_SIZE);
	aura_fpc_put32(request, AURA_FPC_SHARED_SIZE);
	aura_fpc_put32(shared, 10);
	aura_fpc_put32(shared + 4, 4);
	aura_fpc_put32(shared + 8, UINT32_MAX);
}

/* Stock fpc_tee_wait_finger_down at 0x57ec uses sensor subcommand 2. */
static inline void aura_fpc_finger_detect_request(unsigned char *request,
						unsigned char *response,
						unsigned char *shared)
{
	aura_fpc_sensor_init_request(request, response, shared);
	aura_fpc_put32(shared + 4, 2);
}

/* fpc_tee_capture_snapshot at 0x5b5c and capture_image at 0x5890 use 3.
 * This only requests an image inside the TA. No image-output buffer exists.
 */
static inline void aura_fpc_capture_request(unsigned char *request,
					  unsigned char *response,
					  unsigned char *shared)
{
	aura_fpc_sensor_init_request(request, response, shared);
	aura_fpc_put32(shared + 4, 3);
}
#endif
