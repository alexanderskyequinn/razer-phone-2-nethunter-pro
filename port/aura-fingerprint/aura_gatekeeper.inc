/* SPDX-License-Identifier: MIT
 * Included by aura_fpc_bio.c to reuse its checked root-only TEE transport.
 */
#include "aura_gatekeeper_protocol.h"
#define AURA_GK_HANDLE_PATH "/var/lib/aura/fpc-test-store/kali-gatekeeper.handle"
static char gk_handle_path[128] = AURA_GK_HANDLE_PATH;
static bool gk_existing_only;

static int gk_transfer_size(int fd, uint32_t session, struct buffer *wire, size_t request_size, const char *operation)
{
	struct {
		struct tee_ioctl_invoke_arg arg;
		struct tee_ioctl_param params[2];
	} message = {.arg = {.session = session, .num_params = 2}};
	memset(wire->data + AURA_GK_REQUEST_SIZE, 0xff, AURA_GK_RESPONSE_SIZE);
	message.params[0] = memref(wire, TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT, 0, request_size);
	message.params[1] = memref(wire, TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_OUTPUT, AURA_GK_REQUEST_SIZE, AURA_GK_RESPONSE_SIZE);
	struct tee_ioctl_buf_data data = {.buf_ptr = (uintptr_t)&message, .buf_len = sizeof(message)};
	if (ioctl(fd, TEE_IOC_INVOKE, &data) || message.arg.ret) { errno = EIO; return -1; }
	int32_t status = (int32_t)aura_fpc_get32(wire->data + AURA_GK_REQUEST_SIZE);
	printf("Gatekeeper %s: status=%d\n", operation, status);
	/* A positive result can be a throttle interval. Never automatically retry. */
	if (status) { errno = EACCES; return -1; }
	return 0;
}

/* Stock KeymasterUtils constructor, libkeymasterdeviceutils.so 0x17e4/0x18dc.
 * Negotiate the public wire protocol, not OS patch levels or key policy. */
static int gk_initialize(int fd, uint32_t session, struct buffer *wire)
{
	memset(wire->data, 0, wire->size);
	aura_fpc_put32(wire->data, 0x200);
	if (gk_transfer_size(fd, session, wire, 4, "read protocol version")) return -1;
	const unsigned char *reply = wire->data + AURA_GK_REQUEST_SIZE;
	printf("Keymaster public versions: API=%u.%u TA=%u.%u\n",
	       aura_fpc_get32(reply + 4), aura_fpc_get32(reply + 8),
	       aura_fpc_get32(reply + 12), aura_fpc_get32(reply + 16));
	memset(wire->data, 0, wire->size);
	const uint32_t stock_version[] = {0x207, 4, 5, 4, 5, 0};
	for (unsigned i = 0; i < 6; ++i) aura_fpc_put32(wire->data + i * 4, stock_version[i]);
	return gk_transfer_size(fd, session, wire, 24, "negotiate stock protocol version");
}

static int gk_read_handle(unsigned char *handle, size_t *size)
{
	int file = open(gk_handle_path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
	if (file < 0) return errno == ENOENT ? 1 : -1;
	struct stat metadata;
	int result = -1;
	if (fstat(file, &metadata) || !S_ISREG(metadata.st_mode) || metadata.st_uid ||
	    metadata.st_mode & 0077 || metadata.st_nlink != 1 || metadata.st_size <= 0 || metadata.st_size > AURA_GK_MAX_HANDLE) {
		errno = EINVAL; goto done;
	}
	*size = metadata.st_size;
	if (read(file, handle, *size) != (ssize_t)*size) { errno = EIO; goto done; }
	result = 0;
done:
	{ int saved = errno; close(file); errno = saved; }
	return result;
}

static int gk_save_handle(const unsigned char *handle, size_t size)
{
	if (gk_existing_only) { errno = EACCES; return -1; }
	int file = open(gk_handle_path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
	if (file < 0) return -1;
	int result = write(file, handle, size) == (ssize_t)size && !fsync(file) ? 0 : -1;
	int saved = errno;
	if (close(file) && !result) return -1;
	errno = saved;
	return result;
}

static int gk_authorize(int fd, uint32_t fpc_session, struct buffer *xfer,
			struct buffer *shared, const unsigned char *pin, size_t pin_size)
{
	struct buffer name = {.fd = -1}, wire = {.fd = -1};
	unsigned char challenge[8], handle[AURA_GK_MAX_HANDLE] = {0};
	size_t handle_size = 0;
	uint32_t session = 0;
	bool opened = false;
	int result = -1;
	if (bio_hw_auth(fd, fpc_session, xfer, shared)) goto done;
	bio_request(xfer, shared, 3, 2, 16);
	if (bio_reply(fd, fpc_session, xfer, shared, 16, "Enrollment authorization challenge")) goto done;
	memcpy(challenge, shared->data + 8, 8);
	if (!aura_fpc_get32(challenge) && !aura_fpc_get32(challenge + 4)) { errno = EPROTO; goto done; }
	if (alloc_buffer(fd, &name, 4096) || alloc_buffer(fd, &wire, 4096)) goto done;
	memcpy(name.data, "keymaster64", sizeof("keymaster64"));
	if (open_session(fd, &name, &session)) goto done;
	opened = true;
	if (gk_initialize(fd, session, &wire)) goto done;
	int existing = gk_read_handle(handle, &handle_size);
	if (existing < 0) goto done;
	if (existing > 0) {
		/* Missing state must never silently reset an account's secure identity. */
		if (gk_existing_only) { errno = ENOENT; goto done; }
		puts("Setting up the separate Linux Gatekeeper user (UID 1000); Android UID 0 is not modified.");
		if (aura_gk_enroll_request(wire.data, AURA_GK_REQUEST_SIZE, pin, pin_size) ||
		    gk_transfer_size(fd, session, &wire, 32 + pin_size, "PIN enrollment")) goto done;
		const unsigned char *blob;
		if (aura_gk_response_span(wire.data + AURA_GK_REQUEST_SIZE, AURA_GK_RESPONSE_SIZE,
					 AURA_GK_MAX_HANDLE, &blob, &handle_size)) { errno = EPROTO; goto done; }
		memcpy(handle, blob, handle_size);
		if (gk_save_handle(handle, handle_size)) goto done;
		puts("Private Gatekeeper handle saved; PIN is not stored.");
	}
	if (aura_gk_verify_request_for_uid(wire.data, AURA_GK_REQUEST_SIZE, bio_uid, challenge, handle, handle_size, pin, pin_size) ||
	    gk_transfer_size(fd, session, &wire, 32 + handle_size + pin_size, "PIN verification")) goto done;
	const unsigned char *token;
	size_t token_size;
	if (aura_gk_response_span(wire.data + AURA_GK_REQUEST_SIZE, AURA_GK_RESPONSE_SIZE,
				 AURA_GK_TOKEN_SIZE, &token, &token_size) || token_size != AURA_GK_TOKEN_SIZE ||
	    token[0] || memcmp(token + 1, challenge, 8)) { errno = EPROTO; goto done; }
	bio_request(xfer, shared, 3, 3, 8);
	aura_fpc_put32(shared->data + 12, token_size);
	memcpy(shared->data + 16, token, token_size);
	explicit_bzero(wire.data, wire.size);
	if (bio_reply(fd, fpc_session, xfer, shared, 8, "Authorize fingerprint enrollment with Gatekeeper token")) goto done;
	puts("AUTHORIZATION_ACCEPTED: genuine secure PIN verification; token not saved or logged.");
	result = 0;
done:
	if (opened && close_session(fd, session)) result = -1;
	explicit_bzero(challenge, sizeof(challenge));
	explicit_bzero(handle, sizeof(handle));
	if (wire.data) explicit_bzero(wire.data, wire.size);
	if (shared->data) explicit_bzero(shared->data, shared->size);
	free_buffer(&wire);
	free_buffer(&name);
	return result;
}
