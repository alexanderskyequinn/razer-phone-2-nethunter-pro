/* SPDX-License-Identifier: MIT
 * Diagnostic for the experimental QSEECOM TEE ABI. Default is inspect-only.
 * --load-build-info loads signed firmware and sends one stock metadata command.
 * Explicit capture modes return status only; they do not export image data.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <inttypes.h>
#include <linux/tee.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>
#include "aura_fpc_protocol.h"

#define AURA_TEE_IMPL_ID 5u
#define AURA_FPC_APP "fpctzappfingerprint"

struct buffer {
	int fd;
	int id;
	size_t size;
	unsigned char *data;
};

static int check_device(const char *path, bool privileged)
{
	struct tee_ioctl_version_data v = {0};
	int fd = open(path, O_RDWR | O_CLOEXEC);
	if (fd < 0)
		return -1;
	if (ioctl(fd, TEE_IOC_VERSION, &v) < 0)
		goto fail;
	if (v.impl_id != AURA_TEE_IMPL_ID ||
	    !!(v.gen_caps & TEE_GEN_CAP_PRIVILEGED) != privileged ||
	    (v.gen_caps & TEE_GEN_CAP_GP)) {
		errno = EPROTONOSUPPORT;
		goto fail;
	}
	printf("%s: QSEECOM implementation %u, %s\n", path, v.impl_id,
	       privileged ? "privileged loader" : "client");
	return fd;
fail:
	{
		int saved = errno;
		close(fd);
		errno = saved;
		return -1;
	}
}

static void free_buffer(struct buffer *b)
{
	if (b->data)
		munmap(b->data, b->size);
	if (b->fd >= 0)
		close(b->fd);
	b->data = NULL;
	b->fd = -1;
}

static int alloc_buffer(int fd, struct buffer *b, size_t size)
{
	struct tee_ioctl_shm_alloc_data arg = {.size = size};
	b->fd = ioctl(fd, TEE_IOC_SHM_ALLOC, &arg);
	if (b->fd < 0)
		return -1;
	b->id = arg.id;
	b->size = arg.size;
	if (arg.size < size || arg.size > 1024 * 1024 || arg.id < 0) {
		errno = EPROTO;
		goto fail;
	}
	b->data = mmap(NULL, b->size, PROT_READ | PROT_WRITE, MAP_SHARED, b->fd, 0);
	if (b->data == MAP_FAILED) {
		b->data = NULL;
		goto fail;
	}
	memset(b->data, 0, b->size);
	return 0;
fail:
	{
		int saved = errno;
		free_buffer(b);
		errno = saved;
		return -1;
	}
}

static struct tee_ioctl_param memref(const struct buffer *b, uint64_t attr,
				    size_t offset, size_t size)
{
	return (struct tee_ioctl_param){.attr = attr, .a = offset, .b = size, .c = b->id};
}

static int open_session(int fd, const struct buffer *name, uint32_t *session)
{
	size_t size = sizeof(struct tee_ioctl_open_session_arg) + sizeof(struct tee_ioctl_param);
	struct tee_ioctl_open_session_arg *arg = calloc(1, size);
	struct tee_ioctl_buf_data buf;
	int ret;
	if (!arg)
		return -1;
	arg->num_params = 1;
	arg->params[0] = memref(name, TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT,
			       0, sizeof(AURA_FPC_APP));
	buf = (struct tee_ioctl_buf_data){.buf_ptr = (uintptr_t)arg, .buf_len = size};
	ret = ioctl(fd, TEE_IOC_OPEN_SESSION, &buf);
	if (!ret && arg->ret) {
		errno = EIO;
		ret = -1;
	}
	if (!ret)
		*session = arg->session;
	free(arg);
	return ret;
}

static int close_session(int fd, uint32_t session)
{
	struct tee_ioctl_close_session_arg arg = {.session = session};
	return ioctl(fd, TEE_IOC_CLOSE_SESSION, &arg);
}

static int transfer(int fd, uint32_t session, struct buffer *xfer, struct buffer *shared)
{
	size_t size = sizeof(struct tee_ioctl_invoke_arg) + 4 * sizeof(struct tee_ioctl_param);
	struct tee_ioctl_invoke_arg *arg = calloc(1, size);
	struct tee_ioctl_buf_data buf;
	int ret;
	if (!arg)
		return -1;
	arg->session = session;
	arg->num_params = 4;
	arg->params[0] = memref(xfer, TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT, 0, 64);
	arg->params[1] = memref(xfer, TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_OUTPUT, 64, 64);
	arg->params[2] = (struct tee_ioctl_param){.attr = TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INPUT,
		.a = AURA_FPC_ADDRESS_OFFSET, .b = 4};
	arg->params[3] = memref(shared, TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INOUT, 0, AURA_FPC_SHARED_SIZE);
	buf = (struct tee_ioctl_buf_data){.buf_ptr = (uintptr_t)arg, .buf_len = size};
	ret = ioctl(fd, TEE_IOC_INVOKE, &buf);
	if (!ret && arg->ret) {
		errno = EIO;
		ret = -1;
	}
	free(arg);
	return ret;
}

static int build_info(int fd, uint32_t session, struct buffer *xfer, struct buffer *shared)
{
	char text[AURA_FPC_INFO_SIZE + 1];
	int ret;
	aura_fpc_build_info_request(xfer->data, xfer->data + AURA_FPC_XFER_SIZE, shared->data);
	ret = transfer(fd, session, xfer, shared);
	if (ret)
		return ret;
	ret = aura_fpc_decode_info(xfer->data + 64, shared->data, text, sizeof(text));
	if (ret) {
		errno = -ret;
		return -1;
	}
	puts("Firmware build information:");
	for (size_t i = 0; text[i]; ++i) {
		unsigned char ch = text[i];
		putchar((ch >= 32 && ch < 127) || ch == '\n' || ch == '\t' ? ch : '?');
	}
	putchar('\n');
	return 0;
}

static int sensor_command(int fd, uint32_t session, struct buffer *xfer, struct buffer *shared, unsigned command)
{
	if (command == 2)
		aura_fpc_finger_detect_request(xfer->data, xfer->data + AURA_FPC_XFER_SIZE, shared->data);
	else if (command == 3)
		aura_fpc_capture_request(xfer->data, xfer->data + AURA_FPC_XFER_SIZE, shared->data);
	else if (command == 4)
		aura_fpc_sensor_init_request(xfer->data, xfer->data + AURA_FPC_XFER_SIZE, shared->data);
	else { errno = EINVAL; return -1; }
	printf("Sending stock sensor command (10,%u); no automatic retries.\n", command);
	if (transfer(fd, session, xfer, shared))
		return -1;
	uint32_t transport = aura_fpc_get32(xfer->data + AURA_FPC_XFER_SIZE);
	uint32_t status = aura_fpc_get32(shared->data + 8);
	printf("Sensor reply: transport=0x%08" PRIx32 ", status=%" PRId32 "\n",
	       transport, (int32_t)status);
	if (transport || status) {
		errno = !transport && command == 3 && status == 3 ? EAGAIN : EIO;
		return -1;
	}
	return 0;
}

static int finger_detect(int fd, uint32_t session, struct buffer *xfer, struct buffer *shared)
{
	if (sensor_command(fd, session, xfer, shared, 4))
		return -1;
	int result = sensor_command(fd, session, xfer, shared, 2);
	if (!result) {
		puts("Finger detection armed for 60 seconds; observe the IRQ separately. No image capture.");
		sleep(60);
	}
	/* Return to the stock idle state even when arming reports an error. */
	if (sensor_command(fd, session, xfer, shared, 4))
		result = -1;
	if (result) errno = EIO;
	else puts("Finger detection disarmed; no image or template requested.");
	return result;
}

static int capture_once(int fd, uint32_t session, struct buffer *xfer, struct buffer *shared, bool retry)
{
	int irq = -1, result = -1;
	unsigned waited = 0;
	if (sensor_command(fd, session, xfer, shared, 4))
		return -1;
	irq = open("/sys/bus/platform/devices/fingerprint/irq", O_RDONLY | O_CLOEXEC);
	if (irq < 0) goto out;
	puts("Waiting up to 60 seconds for a finger; no image export or enrollment.");
	for (unsigned attempt = 0; attempt < (retry ? 10u : 1u); ++attempt) {
	  bool touched = false;
	  if (sensor_command(fd, session, xfer, shared, 2)) goto out;
	  for (; waited < 600; ++waited) {
		char value[2];
		if (lseek(irq, 0, SEEK_SET) < 0 || read(irq, value, sizeof(value)) != 2) goto out;
		if ((value[0] != '0' && value[0] != '1') || value[1] != '\n') { errno = EPROTO; goto out; }
		if (value[0] == '1') { touched = true; break; }
		usleep(100000);
	  }
	  if (!touched) { result = -1; errno = ETIMEDOUT; goto out; }
	  printf("Finger IRQ observed; secure snapshot attempt %u.\n", attempt + 1);
	  result = sensor_command(fd, session, xfer, shared, 3);
	  if (!result) { puts("Secure snapshot status=0; no image exported, saved, or enrolled."); break; }
	  if (!retry || errno != EAGAIN) break;
	}
out:
	{
		int saved = errno;
		if (irq >= 0) close(irq);
		if (sensor_command(fd, session, xfer, shared, 4)) return -1;
		errno = saved;
		return result;
	}
}

int main(int argc, char **argv)
{
	bool sensor = argc == 2 && !strcmp(argv[1], "--sensor-init");
	bool detect = argc == 2 && !strcmp(argv[1], "--finger-detect-test");
	bool retry = argc == 2 && !strcmp(argv[1], "--capture-test");
	bool capture = retry || (argc == 2 && !strcmp(argv[1], "--capture-once"));
	bool active = sensor || detect || capture || (argc == 2 && !strcmp(argv[1], "--load-build-info"));
	struct buffer name = {.fd = -1}, client_name = {.fd = -1};
	struct buffer xfer = {.fd = -1}, shared = {.fd = -1};
	int client = -1, loader = -1, result = 1;
	uint32_t load_session = 0, session = 0;
	bool loaded = false, opened = false;
	const char *step = "open client";

	if (argc > 2 || (argc == 2 && !active && strcmp(argv[1], "--inspect"))) {
		fprintf(stderr, "Usage: %s [--inspect | --load-build-info | --sensor-init | --finger-detect-test | --capture-once | --capture-test]\n", argv[0]);
		return 2;
	}
	setvbuf(stdout, NULL, _IONBF, 0);
	client = check_device("/dev/tee0", false);
	if (client < 0)
		goto error;
	if (!active) {
		puts("Inspection complete; no firmware loaded and no commands sent.");
		result = 0;
		goto done;
	}
	step = "open privileged loader";
	loader = check_device("/dev/teepriv0", true);
	if (loader < 0)
		goto error;
	step = "allocate app name";
	if (alloc_buffer(loader, &name, 4096) || alloc_buffer(client, &client_name, 4096))
		goto error;
	memcpy(name.data, AURA_FPC_APP, sizeof(AURA_FPC_APP));
	memcpy(client_name.data, AURA_FPC_APP, sizeof(AURA_FPC_APP));
	step = "load signed firmware";
	if (open_session(loader, &name, &load_session))
		goto error;
	loaded = true;
	step = "open firmware session";
	if (open_session(client, &client_name, &session))
		goto error;
	opened = true;
	step = "allocate transfer buffers";
	if (alloc_buffer(client, &xfer, 4096) || alloc_buffer(client, &shared, AURA_FPC_SHARED_SIZE))
		goto error;
	step = capture ? "secure capture test" : detect ? "finger-detect test" : sensor ? "stock sensor initialization" : "read build information";
	if (capture ? capture_once(client, session, &xfer, &shared, retry) :
	    detect ? finger_detect(client, session, &xfer, &shared) :
	    sensor ? sensor_command(client, session, &xfer, &shared, 4) :
	    build_info(client, session, &xfer, &shared))
		goto error;
	result = 0;
	goto done;
error:
	fprintf(stderr, "%s: %s\n", step, strerror(errno));
done:
	if (opened && close_session(client, session)) {
		perror("close client session");
		result = 1;
	}
	if (loaded && close_session(loader, load_session)) {
		perror("close load session");
		result = 1;
	}
	free_buffer(&shared);
	free_buffer(&xfer);
	free_buffer(&client_name);
	free_buffer(&name);
	if (client >= 0)
		close(client);
	if (loader >= 0)
		close(loader);
	return result;
}
