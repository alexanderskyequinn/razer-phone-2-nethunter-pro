/* SPDX-License-Identifier: MIT */
#ifndef AURA_GATEKEEPER_PROTOCOL_H
#define AURA_GATEKEEPER_PROTOCOL_H
#include "aura_fpc_protocol.h"

#define AURA_GK_UID 1000u
#define AURA_GK_REQUEST_SIZE 1024u
#define AURA_GK_RESPONSE_SIZE 3072u
#define AURA_GK_MAX_HANDLE 512u
#define AURA_GK_TOKEN_SIZE 69u

/* Stock GatekeeperHalDevice::enroll at 0x3058. A new Linux user handle
 * only: no prior Android user handle or password is read or replaced. */
static inline int aura_gk_enroll_request_for_uid(unsigned char *out, size_t size, uint32_t uid,
				       const unsigned char *pin, size_t pin_size)
{
	/* UID 0 belongs to stock Android. Desktop callers must resolve and
	 * authorize a real account before entering this wire-format helper. */
	if (!out || !pin || uid < 1000 || uid == UINT32_MAX ||
	    size < AURA_GK_REQUEST_SIZE || pin_size < 4 || pin_size > 64) return -1;
	memset(out, 0, size);
	aura_fpc_put32(out, 0x1001);
	aura_fpc_put32(out + 4, uid);
	aura_fpc_put32(out + 24, 32);
	aura_fpc_put32(out + 28, pin_size);
	memcpy(out + 32, pin, pin_size);
	return 0;
}

/* Stock verify at 0x33d0: challenge is a packed little-endian uint64. */
static inline int aura_gk_verify_request_for_uid(unsigned char *out, size_t size, uint32_t uid,
				       const unsigned char challenge[8],
				       const unsigned char *handle, size_t handle_size,
				       const unsigned char *pin, size_t pin_size)
{
	if (!out || !challenge || !handle || !pin || uid < 1000 || uid == UINT32_MAX ||
	    size < AURA_GK_REQUEST_SIZE || !handle_size || handle_size > AURA_GK_MAX_HANDLE ||
	    pin_size < 4 || pin_size > 64) return -1;
	memset(out, 0, size);
	aura_fpc_put32(out, 0x1002);
	aura_fpc_put32(out + 4, uid);
	memcpy(out + 8, challenge, 8);
	aura_fpc_put32(out + 16, 32);
	aura_fpc_put32(out + 20, handle_size);
	aura_fpc_put32(out + 24, 32 + handle_size);
	aura_fpc_put32(out + 28, pin_size);
	memcpy(out + 32, handle, handle_size);
	memcpy(out + 32 + handle_size, pin, pin_size);
	return 0;
}

/* Preserve the existing engineering backend's account and wire format until
 * the stock integration explicitly supplies its authorized account. */
static inline int aura_gk_enroll_request(unsigned char *out, size_t size,
				       const unsigned char *pin, size_t pin_size)
{
	return aura_gk_enroll_request_for_uid(out, size, AURA_GK_UID, pin, pin_size);
}

static inline int aura_gk_verify_request(unsigned char *out, size_t size,
				       const unsigned char challenge[8],
				       const unsigned char *handle, size_t handle_size,
				       const unsigned char *pin, size_t pin_size)
{
	return aura_gk_verify_request_for_uid(out, size, AURA_GK_UID, challenge,
					     handle, handle_size, pin, pin_size);
}

static inline int aura_gk_response_span(const unsigned char *response, size_t size,
				      size_t max_size, const unsigned char **blob, size_t *blob_size)
{
	if (!response || !blob || !blob_size || size < 12 || aura_fpc_get32(response)) return -1;
	uint32_t offset = aura_fpc_get32(response + 4), length = aura_fpc_get32(response + 8);
	if (offset < 12 || offset > size || !length || length > max_size || length > size - offset) return -1;
	*blob = response + offset;
	*blob_size = length;
	return 0;
}
#endif
