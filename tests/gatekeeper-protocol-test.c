/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include "../port/aura-fingerprint/aura_gatekeeper_protocol.h"

int main(void)
{
	unsigned char request[1024], response[3072] = {0};
	const unsigned char pin[] = "2468";
	const unsigned char challenge[8] = {1,2,3,4,5,6,7,8};
	const unsigned char handle[58] = {3,4,5};
	assert(!aura_gk_enroll_request(request, sizeof(request), pin, 4));
	assert(aura_fpc_get32(request) == 0x1001 && aura_fpc_get32(request+4) == 1000);
	for (unsigned i = 8; i < 24; ++i) assert(!request[i]);
	assert(aura_fpc_get32(request+24) == 32 && aura_fpc_get32(request+28) == 4);
	assert(!memcmp(request+32, pin, 4));
	assert(aura_gk_enroll_request(request, 20, pin, 4) == -1);
	assert(aura_gk_enroll_request(request, sizeof(request), pin, 3) == -1);
	assert(!aura_gk_verify_request(request, sizeof(request), challenge, handle, sizeof(handle), pin, 4));
	assert(aura_fpc_get32(request) == 0x1002);
	assert(!memcmp(request+8, challenge, 8));
	assert(aura_fpc_get32(request+16) == 32 && aura_fpc_get32(request+20) == 58);
	assert(aura_fpc_get32(request+24) == 90 && aura_fpc_get32(request+28) == 4);
	assert(!memcmp(request+32, handle, 58) && !memcmp(request+90, pin, 4));
	assert(aura_gk_verify_request(request, sizeof(request), challenge, handle, 513, pin, 4) == -1);
	/* Different users change only the explicit UID field; the challenge,
	 * opaque handle and credential spans retain their checked layouts. */
	unsigned char account_request[1024];
	assert(!aura_gk_verify_request(request, sizeof(request), challenge, handle, sizeof(handle), pin, 4));
	assert(!aura_gk_verify_request_for_uid(account_request, sizeof(account_request), 60001, challenge, handle, sizeof(handle), pin, 4));
	assert(aura_fpc_get32(account_request + 4) == 60001);
	memcpy(account_request + 4, request + 4, 4);
	assert(!memcmp(account_request, request, sizeof(request)));
	assert(!aura_gk_enroll_request_for_uid(account_request, sizeof(account_request), 1001, pin, 4));
	assert(aura_fpc_get32(account_request + 4) == 1001);
	uint32_t rejected_uids[] = {0, 999, UINT32_MAX};
	for (unsigned i = 0; i < sizeof(rejected_uids)/sizeof(rejected_uids[0]); ++i) {
		memset(account_request, 0xa5, sizeof(account_request));
		assert(aura_gk_enroll_request_for_uid(account_request, sizeof(account_request), rejected_uids[i], pin, 4) == -1);
		assert(aura_gk_verify_request_for_uid(account_request, sizeof(account_request), rejected_uids[i], challenge, handle, sizeof(handle), pin, 4) == -1);
		for (unsigned j = 0; j < sizeof(account_request); ++j) assert(account_request[j] == 0xa5);
	}
	assert(aura_gk_enroll_request_for_uid(NULL, sizeof(request), 1000, pin, 4) == -1);
	assert(aura_gk_enroll_request_for_uid(request, sizeof(request), 1000, NULL, 4) == -1);
	assert(aura_gk_verify_request_for_uid(request, sizeof(request), 1000, NULL, handle, sizeof(handle), pin, 4) == -1);
	const unsigned char *blob = NULL;
	size_t blob_size = 0;
	aura_fpc_put32(response+4, 12); aura_fpc_put32(response+8, 69);
	assert(!aura_gk_response_span(response, sizeof(response), 69, &blob, &blob_size));
	assert(blob == response+12 && blob_size == 69);
	aura_fpc_put32(response+4, UINT32_MAX);
	assert(aura_gk_response_span(response, sizeof(response), 69, &blob, &blob_size) == -1);
	aura_fpc_put32(response+4, 3070);
	assert(aura_gk_response_span(response, sizeof(response), 69, &blob, &blob_size) == -1);
	aura_fpc_put32(response+4, 12); aura_fpc_put32(response+8, 70);
	assert(aura_gk_response_span(response, sizeof(response), 69, &blob, &blob_size) == -1);
	aura_fpc_put32(response+8, 69); aura_fpc_put32(response, 1000);
	assert(aura_gk_response_span(response, sizeof(response), 69, &blob, &blob_size) == -1);
	puts("PASS: stock Gatekeeper wire layouts, bounds and throttle refusal");
	return 0;
}
