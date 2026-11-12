/* SPDX-License-Identifier: MIT
 * Enrollment bring-up. Reuses the tested transport without exposing arbitrary
 * commands. No template file is loaded or saved by the preflight mode.
 */
#define main aura_fpc_existing_diagnostic_main
#include "aura_fpc_probe.c"
#undef main
#include <sys/stat.h>
#include <signal.h>
#include <sys/resource.h>
#include <sys/file.h>
#include <sys/prctl.h>
#include <sys/random.h>
#include <poll.h>
#include <time.h>
#include "aura_fpc_account.h"

static volatile sig_atomic_t bio_cancelled;
static void bio_cancel(int signal_number)
{
	(void)signal_number;
	bio_cancelled = 1;
}

#define BIO_DB_NAME "aura-fpc-test.db"
#define BIO_DB_PATH "/var/lib/aura/fpc-test-store/" BIO_DB_NAME
static uint32_t bio_uid = 1000;
static char bio_db_name[64] = BIO_DB_NAME;
static char bio_db_path[128] = BIO_DB_PATH;

static int bio_account_lock(void)
{
	const char *parents[] = {"/var", "/var/lib", "/var/lib/aura",
		"/var/lib/aura/fpc-test-store", "/var/lib/aura/fpc-test-store/accounts"};
	struct stat st;
	for (unsigned i = 0; i < sizeof(parents)/sizeof(parents[0]); ++i) {
		if (lstat(parents[i], &st) || !S_ISDIR(st.st_mode) || st.st_uid ||
		    (st.st_mode & (i >= 3 ? 0077 : 0022))) { errno = EACCES; return -1; }
	}
	int fd = open("/run/aura-fpc-test.lock", O_CREAT | O_RDWR | O_CLOEXEC | O_NOFOLLOW, 0600);
	if (fd < 0) return -1;
	if (fstat(fd, &st) || !S_ISREG(st.st_mode) || st.st_uid ||
	    (st.st_mode & 0077) || st.st_nlink != 1 || flock(fd, LOCK_EX | LOCK_NB)) {
		int saved = errno ? errno : EACCES;
		close(fd); errno = saved; return -1;
	}
	return fd;
}

static void bio_request(struct buffer *xfer, struct buffer *shared,
			unsigned module, unsigned command, unsigned status_offset)
{
	memset(xfer->data, 0, xfer->size);
	memset(xfer->data + 64, 0xff, 64);
	memset(shared->data, 0, shared->size);
	aura_fpc_put32(xfer->data, AURA_FPC_SHARED_SIZE);
	aura_fpc_put32(shared->data, module);
	aura_fpc_put32(shared->data + 4, command);
	aura_fpc_put32(shared->data + status_offset, UINT32_MAX);
}

static int bio_reply(int fd, uint32_t session, struct buffer *xfer,
		     struct buffer *shared, unsigned offset, const char *label)
{
	if (transfer(fd, session, xfer, shared)) return -1;
	uint32_t transport = aura_fpc_get32(xfer->data + 64);
	int32_t status = (int32_t)aura_fpc_get32(shared->data + offset);
	printf("%s: transport=0x%08" PRIx32 " status=%" PRId32 "\n", label, transport, status);
	if (transport || status) { errno = EIO; return -1; }
	return 0;
}

/* Stock fpc_tee_init_hw_auth at 0x6f08: request a wrapped auth key for
 * authenticator type 2, then hand that opaque blob to the signed FPC TA.
 * No key bytes or auth-token bytes are printed or written to disk. */
static int bio_hw_auth(int fd, uint32_t fpc_session, struct buffer *xfer, struct buffer *shared)
{
	struct buffer name = {.fd = -1}, wire = {.fd = -1};
	uint32_t km_session = 0;
	bool opened = false;
	int result = -1;
	if (alloc_buffer(fd, &name, 4096) || alloc_buffer(fd, &wire, 4096)) goto done;
	memcpy(name.data, "keymaster64", sizeof("keymaster64"));
	if (open_session(fd, &name, &km_session)) goto done;
	opened = true;
	aura_fpc_put32(wire.data, 0x205);
	aura_fpc_put32(wire.data + 4, 2);
	memset(wire.data + 64, 0xff, 960);
	struct {
		struct tee_ioctl_invoke_arg arg;
		struct tee_ioctl_param params[2];
	} message = {.arg = {.session = km_session, .num_params = 2}};
	message.params[0] = memref(&wire, TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT, 0, 64);
	message.params[1] = memref(&wire, TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_OUTPUT, 64, 960);
	struct tee_ioctl_buf_data data = {.buf_ptr = (uintptr_t)&message, .buf_len = sizeof(message)};
	if (ioctl(fd, TEE_IOC_INVOKE, &data) || message.arg.ret) { errno = EIO; goto done; }
	int32_t status = (int32_t)aura_fpc_get32(wire.data + 64);
	printf("Keymaster wrapped-auth-key request: status=%d\n", status);
	if (status) { errno = EACCES; goto done; }
	uint32_t offset = aura_fpc_get32(wire.data + 68), length = aura_fpc_get32(wire.data + 72);
	if (offset < 12 || offset > 960 || !length || length > 960 - offset) { errno = EPROTO; goto done; }
	bio_request(xfer, shared, 3, 5, 8);
	aura_fpc_put32(shared->data + 12, length);
	memcpy(shared->data + 16, wire.data + 64 + offset, length);
	explicit_bzero(wire.data, wire.size);
	if (bio_reply(fd, fpc_session, xfer, shared, 8, "Initialize fingerprint hardware authentication")) goto done;
	puts("Hardware authentication initialized. No Gatekeeper user enrolled or token minted.");
	result = 0;
done:
	if (opened && close_session(fd, km_session)) result = -1;
	if (wire.data) explicit_bzero(wire.data, wire.size);
	free_buffer(&wire);
	free_buffer(&name);
	return result;
}

#include "aura_gatekeeper.inc"

/* Account enrollment takes the existing firmware PIN only through a pipe.
 * No stdio buffering, argument, environment or disk copy of the credential.
 * The caller owns account authorization and the standard prompt lifecycle. */
static int bio_account_pin(unsigned char *pin, size_t *size)
{
	struct stat st;
	if (fstat(STDIN_FILENO, &st) || !S_ISFIFO(st.st_mode)) { errno = EINVAL; return -1; }
	struct timespec start, now;
	if (clock_gettime(CLOCK_MONOTONIC, &start)) return -1;
	*size = 0;
	for (;;) {
		if (bio_cancelled) { errno = ECANCELED; return -1; }
		if (clock_gettime(CLOCK_MONOTONIC, &now)) return -1;
		if (now.tv_sec - start.tv_sec >= 125) { errno = ETIMEDOUT; return -1; }
		struct pollfd input = {.fd = STDIN_FILENO, .events = POLLIN};
		int ready = poll(&input, 1, 100);
		if (ready < 0) { if (errno == EINTR) continue; return -1; }
		if (!ready) continue;
		unsigned char c = 0;
		ssize_t count = read(STDIN_FILENO, &c, 1);
		if (count != 1) { errno = EINVAL; return -1; }
		if (c == '\n') { if (*size >= 4) return 0; errno = EINVAL; return -1; }
		if (c < '0' || c > '9' || *size >= 64) { errno = EINVAL; return -1; }
		pin[(*size)++] = c;
	}
}

static int enrollment_preflight(int fd, uint32_t session, struct buffer *xfer, struct buffer *shared,
				const unsigned char *pin, size_t pin_size)
{
	/* Stock fpc_tee_get_finger_ids: capacity at 12, at most five IDs at 16. */
	bio_request(xfer, shared, 11, 7, 8);
	aura_fpc_put32(shared->data + 12, 5);
	if (bio_reply(fd, session, xfer, shared, 8, "Resident template count")) return -1;
	uint32_t count = aura_fpc_get32(shared->data + 12);
	if (count > 5) { errno = EPROTO; return -1; }
	printf("Resident template count=%u; identifiers are not logged.\n", count);
	if (count) { errno = EEXIST; return -1; }
	if (pin) {
		bio_request(xfer, shared, 11, 6, 8);
		if (bio_reply(fd, session, xfer, shared, 8, "Initialize empty Linux fingerprint database")) return -1;
		bio_request(xfer, shared, 11, 9, 8);
		aura_fpc_put32(shared->data + 12, bio_uid);
		if (bio_reply(fd, session, xfer, shared, 8, "Select Linux fingerprint group")) return -1;
		if (gk_authorize(fd, session, xfer, shared, pin, pin_size)) return -1;
		bio_request(xfer, shared, 11, 0, 8);
		return bio_reply(fd, session, xfer, shared, 8, "Begin authorized enrollment");
	}
	/* fpc_tee_get_enrol_challenge uses status at 16, challenge at 8. */
	bio_request(xfer, shared, 3, 2, 16);
	if (bio_reply(fd, session, xfer, shared, 16, "Enrollment challenge")) return -1;
	if (!aura_fpc_get32(shared->data + 8) && !aura_fpc_get32(shared->data + 12)) {
		errno = EPROTO; return -1;
	}
	puts("Nonzero enrollment challenge received; value not logged.");
	/* A fresh, empty resident DB only; no existing template file is opened. */
	bio_request(xfer, shared, 11, 6, 8);
	if (bio_reply(fd, session, xfer, shared, 8, "Initialize empty resident database")) return -1;
	bio_request(xfer, shared, 11, 0, 8);
	if (bio_reply(fd, session, xfer, shared, 8, "Begin enrollment")) return -1;
	puts("Enrollment session accepted.");
	return 0;
}

/* Stock status is signed; some sensor and enrollment replies use positive
 * values. Never interpret a transport failure as a biometric result. */
static int bio_status(int fd, uint32_t session, struct buffer *xfer,
		      struct buffer *shared, int32_t *status)
{
	if (transfer(fd, session, xfer, shared)) return -1;
	if (aura_fpc_get32(xfer->data + 64)) { errno = EIO; return -1; }
	*status = (int32_t)aura_fpc_get32(shared->data + 8);
	if (*status < 0) { errno = EIO; return -1; }
	return 0;
}

static int bio_pause(unsigned *budget)
{
	if (bio_cancelled) { errno = ECANCELED; return -1; }
	if (!*budget) { errno = ETIMEDOUT; return -1; }
	--*budget;
	return usleep(100000);
}

/* Keep the captured image inside the TA until enroll/identify has consumed it.
 * The older capture diagnostic deliberately idles immediately and cannot be
 * used here. This sequence follows the stock HAL's lift/arm/capture loop. */
static int bio_capture(int fd, uint32_t session, struct buffer *xfer,
		       struct buffer *shared, unsigned *budget)
{
	int32_t status;
	puts("Lift finger, then cover the sensor without pressing the button.");
	for (;;) {
		if (bio_cancelled) { errno = ECANCELED; return -1; }
		bio_request(xfer, shared, 10, 0, 8);
		if (bio_status(fd, session, xfer, shared, &status)) return -1;
		if (status > 0) break;
		if (bio_pause(budget)) return -1;
	}
	puts("FINGER_LIFTED: place your finger on the sensor.");
	int irq = open("/sys/bus/platform/devices/fingerprint/irq", O_RDONLY | O_CLOEXEC);
	if (irq < 0) return -1;
	int result = -1;
	unsigned retry_count = 0;
	for (unsigned attempt = 0; attempt < 10; ++attempt) {
		if (sensor_command(fd, session, xfer, shared, 2)) goto out;
		for (;;) {
			char value[2];
			if (lseek(irq, 0, SEEK_SET) < 0 || read(irq, value, 2) != 2) goto out;
			if ((value[0] != '0' && value[0] != '1') || value[1] != '\n') { errno = EPROTO; goto out; }
			if (value[0] == '1') break;
			if (bio_pause(budget)) goto out;
		}
		bio_request(xfer, shared, 10, 3, 8);
		if (bio_status(fd, session, xfer, shared, &status)) break;
		printf("Secure capture status=%d\n", status);
		if (!status) { result = 0; break; }
		/* Stock enrollment caller at 0x3dac/0x3dc8 requests a fresh
		 * capture for 1 and 4 without submitting the image to enrol. */
		if (status == 1 || status == 4) { result = 1; break; }
		if (status != 3) { errno = EPROTO; break; }
		++retry_count;
		errno = EAGAIN;
	}
	/* Stock 0x5b00 maps ten status-3 captures to recoverable status 4. */
	if (retry_count == 10) { puts("Capture retry limit: request a fresh touch."); result = 1; }
out:
	{ int saved = errno; close(irq); errno = saved; }
	/* Stock capture idles on nonzero results before the caller retries. */
	if (result && sensor_command(fd, session, xfer, shared, 4)) return -1;
	return result;
}

static int bio_database(int fd, uint32_t session, struct buffer *xfer,
			struct buffer *shared, bool store)
{
	bio_request(xfer, shared, 2, store ? 12 : 11, 8);
	size_t name_size = strlen(bio_db_name) + 1;
	aura_fpc_put32(shared->data + 12, name_size);
	memcpy(shared->data + 16, bio_db_name, name_size);
	return bio_reply(fd, session, xfer, shared, 8, store ? "Save private template database" : "Load private template database");
}

static int bio_single_id(int fd, uint32_t session, struct buffer *xfer,
			 struct buffer *shared, uint32_t *id)
{
	bio_request(xfer, shared, 11, 7, 8);
	aura_fpc_put32(shared->data + 12, 5);
	if (bio_reply(fd, session, xfer, shared, 8, "Validate single enrolled template")) return -1;
	if (aura_fpc_get32(shared->data + 12) != 1 || !aura_fpc_get32(shared->data + 16)) {
		errno = EPROTO; return -1;
	}
	*id = aura_fpc_get32(shared->data + 16);
	return 0;
}

static int bio_enroll(int fd, uint32_t session, struct buffer *xfer, struct buffer *shared,
			const unsigned char *pin, size_t pin_size)
{
	if (enrollment_preflight(fd, session, xfer, shared, pin, pin_size)) return -1;
	unsigned budget = 1800;
	for (unsigned sample = 0; sample < 100; ++sample) {
		if (bio_cancelled) { errno = ECANCELED; return -1; }
		int captured = bio_capture(fd, session, xfer, shared, &budget);
		if (captured < 0) return -1;
		if (captured > 0) { puts("Capture needs a new touch; sample not submitted."); continue; }
		bio_request(xfer, shared, 11, 1, 8);
		int32_t status;
		if (bio_status(fd, session, xfer, shared, &status)) return -1;
		uint32_t remaining = aura_fpc_get32(shared->data + 12);
		printf("Enrollment sample %u: status=%d remaining=%u\n", sample + 1, status, remaining);
		if (remaining > 100 || status > 6) { errno = EPROTO; return -1; }
		if (status == 2 || status == 3) { errno = EIO; return -1; }
		if (status) continue;
		if (remaining) { errno = EPROTO; return -1; }
		bio_request(xfer, shared, 11, 2, 8);
		if (bio_reply(fd, session, xfer, shared, 8, "Finish enrollment")) return -1;
		uint32_t enrolled = aura_fpc_get32(shared->data + 12), listed = 0;
		if (!enrolled) { errno = EPROTO; return -1; }
		if (bio_single_id(fd, session, xfer, shared, &listed)) return -1;
		if (listed != enrolled) { errno = EPROTO; return -1; }
		if (bio_database(fd, session, xfer, shared, true)) return -1;
		puts("ENROLLMENT_SAVED: one private template; no image exported.");
		return 0;
	}
	errno = EAGAIN;
	return -1;
}

static int bio_verify(int fd, uint32_t session, struct buffer *xfer,
		      struct buffer *shared, bool capture)
{
	uint32_t expected = 0;
	if (bio_database(fd, session, xfer, shared, false)) return -1;
	/* Stock set_active_group loads the DB (HAL 0x3a98), then selects its
	 * group (0x3ad8). A fresh session does not inherit enrollment's group. */
	bio_request(xfer, shared, 11, 9, 8);
	aura_fpc_put32(shared->data + 12, bio_uid);
	if (bio_reply(fd, session, xfer, shared, 8, "Select saved Linux fingerprint group") ||
	    bio_single_id(fd, session, xfer, shared, &expected)) return -1;
	if (!capture) { puts("DATABASE_RELOADED: one enrolled template."); return 0; }
	/* Stock authentication worker 0x41b8 calls set_auth_challenge (0x675c)
	 * before its capture/identify loop. The challenge is request data, not an
	 * authorization token; matching still comes only from the secure firmware.
	 * Use a fresh nonce and never log it or weaken the biometric decision. */
	bio_request(xfer, shared, 3, 1, 16);
	for (size_t filled = 0; filled < 8;) {
		if (bio_cancelled) { errno = ECANCELED; return -1; }
		ssize_t count = getrandom(shared->data + 8 + filled, 8 - filled, 0);
		if (count < 0 && errno == EINTR) continue;
		if (count <= 0) { if (!count) errno = EIO; return -1; }
		filled += count;
	}
	if (bio_reply(fd, session, xfer, shared, 16, "Initialize verification challenge")) return -1;
	unsigned budget = 600;
	for (unsigned attempt = 0; attempt < 10; ++attempt) {
	int captured = bio_capture(fd, session, xfer, shared, &budget);
	if (captured < 0) return -1;
	if (captured > 0) { puts("Verification retry: capture"); continue; }
	bio_request(xfer, shared, 11, 3, 8);
	int32_t status;
	if (bio_status(fd, session, xfer, shared, &status)) return -1;
	printf("Verification identify status=%" PRId32 "\n", status);
	/* Stock authentication maps identify status 2 to insufficient acquisition
	 * and tries another capture. It is neither a match nor a hard failure. */
	if (status == 2) {
		puts("Verification retry: identify-quality");
		if (sensor_command(fd, session, xfer, shared, 4)) return -1;
		continue;
	}
	if (status) { errno = EPROTO; return -1; }
	/* Stock identify wrapper logs these two acquisition metrics at 0x60ac.
	 * Neither is an image, template, identifier, token, or matching threshold. */
	printf("Capture metrics: coverage=%" PRIu32 " quality=%" PRIu32 "\n",
		aura_fpc_get32(shared->data + 16), aura_fpc_get32(shared->data + 20));
	uint32_t matched = aura_fpc_get32(shared->data + 12);
	if (!matched) { puts("NO_MATCH"); return 3; }
	if (matched != expected) { errno = EPROTO; return -1; }
	puts("MATCH: firmware identified the stored template.");
	return 0;
	}
	errno = EAGAIN;
	return -1;
}

int main(int argc, char **argv)
{
	struct buffer name = {.fd=-1}, client_name = {.fd=-1}, xfer = {.fd=-1}, shared = {.fd=-1};
	int client = -1, loader = -1, account_lock = -1, result = 1;
	uint32_t load_session = 0, session = 0;
	bool loaded = false, opened = false, sensor_active = false;
	unsigned char pin[66] = {0};
	size_t pin_size = 0;
	bool preflight = argc == 2 && !strcmp(argv[1], "--enrollment-preflight");
	bool account_enroll = argc == 5 && !strcmp(argv[1], "--account-enroll");
	bool authorized_enroll = account_enroll || (argc == 2 && !strcmp(argv[1], "--authorized-enroll"));
	bool enroll = authorized_enroll || (argc == 2 && !strcmp(argv[1], "--enroll-test"));
	bool account_verify = argc == 5 && !strcmp(argv[1], "--account-verify");
	bool account_check = argc == 5 && !strcmp(argv[1], "--account-check");
	bool account_mode = account_verify || account_check || account_enroll;
	if (account_mode && (geteuid() || aura_account_database(argv[2], argv[3], argv[4], &bio_uid,
		bio_db_name, sizeof(bio_db_name), bio_db_path, sizeof(bio_db_path)))) return 2;
	if (account_enroll) {
		gk_existing_only = true;
		/* UID 1000 must reuse its existing handle, never create a replacement. */
		if (bio_uid != 1000)
			snprintf(gk_handle_path, sizeof(gk_handle_path),
			         "/var/lib/aura/fpc-test-store/accounts/u%u-gatekeeper.handle", bio_uid);
	}
	bool verify = account_verify || (argc == 2 && !strcmp(argv[1], "--verify-test"));
	bool check = account_check || (argc == 2 && !strcmp(argv[1], "--check-database"));
	bool auth_check = argc == 2 && !strcmp(argv[1], "--auth-preflight");
	bool authorization = argc == 2 && !strcmp(argv[1], "--authorization-test");
	if (!preflight && !enroll && !verify && !check && !auth_check && !authorization) {
		fprintf(stderr, "Usage: %s --enrollment-preflight | --enroll-test | --authorized-enroll | --verify-test | --check-database | --auth-preflight | --authorization-test\n", argv[0]); return 2;
	}
	setvbuf(stdout, NULL, _IONBF, 0);
	struct sigaction action = {.sa_handler = bio_cancel};
	sigemptyset(&action.sa_mask);
	if (sigaction(SIGTERM, &action, NULL) || sigaction(SIGINT, &action, NULL)) goto error;
	if (account_mode) {
		struct rlimit no_core = {0, 0};
		if (setrlimit(RLIMIT_CORE, &no_core)) goto error;
		pid_t parent = getppid();
		if (parent == 1 || prctl(PR_SET_PDEATHSIG, SIGTERM) || getppid() != parent) {
			errno = ECANCELED; goto error;
		}
		account_lock = bio_account_lock();
		if (account_lock < 0) goto error;
	}
	if (authorized_enroll || authorization) {
		struct rlimit no_core = {0, 0};
		if (setrlimit(RLIMIT_CORE, &no_core) || mlock(pin, sizeof(pin))) goto error;
		if (account_enroll) {
			if (bio_account_pin(pin, &pin_size)) goto error;
		} else {
		if (!fgets((char *)pin, sizeof(pin), stdin)) { errno = EINVAL; goto error; }
		pin_size = strcspn((char *)pin, "\n");
		if (pin_size < 4 || pin_size > 64 || pin[pin_size] != '\n') { errno = EINVAL; goto error; }
		pin[pin_size] = 0;
		for (size_t i = 0; i < pin_size; ++i)
			if (pin[i] < '0' || pin[i] > '9') { errno = EINVAL; goto error; }
		}
	}
	if (!preflight && !auth_check && !authorization) {
		struct stat st;
		int exists = lstat(bio_db_path, &st);
		if (enroll) {
			if (!exists) { errno = EEXIST; goto error; }
			if (errno != ENOENT) goto error;
		} else if (exists || !S_ISREG(st.st_mode) || st.st_uid ||
			   (st.st_mode & 0077) || (account_mode && st.st_nlink != 1) || st.st_size <= 0 || st.st_size > 1048576) {
			errno = EINVAL; goto error;
		}
	}
	client = check_device("/dev/tee0", false);
	if (client < 0) goto error;
	loader = check_device("/dev/teepriv0", true);
	if (loader < 0) goto error;
	if (alloc_buffer(loader, &name, 4096) || alloc_buffer(client, &client_name, 4096)) goto error;
	memcpy(name.data, AURA_FPC_APP, sizeof(AURA_FPC_APP));
	memcpy(client_name.data, AURA_FPC_APP, sizeof(AURA_FPC_APP));
	if (open_session(loader, &name, &load_session)) goto error;
	loaded = true;
	if (open_session(client, &client_name, &session)) goto error;
	opened = true;
	if (alloc_buffer(client, &xfer, 4096) || alloc_buffer(client, &shared, 4096)) goto error;
	if (enroll || verify) {
		sensor_active = true;
		if (sensor_command(client, session, &xfer, &shared, 4)) goto error;
	}
	int operation = auth_check ? bio_hw_auth(client, session, &xfer, &shared) :
		authorization ? gk_authorize(client, session, &xfer, &shared, pin, pin_size) :
		preflight ? enrollment_preflight(client, session, &xfer, &shared, NULL, 0) :
		enroll ? bio_enroll(client, session, &xfer, &shared, authorized_enroll ? pin : NULL, pin_size) :
		bio_verify(client, session, &xfer, &shared, verify);
	if (operation < 0) goto error;
	result = operation;
	goto done;
error:
	if (account_mode && bio_cancelled) result = 4;
	else if (account_mode && errno == EAGAIN) result = 5;
	perror("Fingerprint test stopped");
done:
	explicit_bzero(pin, sizeof(pin));
	if (authorized_enroll || authorization) munlock(pin, sizeof(pin));
	if (sensor_active && sensor_command(client, session, &xfer, &shared, 4)) { perror("idle sensor"); result = 1; }
	if (opened && close_session(client, session)) { perror("close client"); result = 1; }
	if (loaded && close_session(loader, load_session)) { perror("close loader"); result = 1; }
	struct buffer *buffers[] = {&shared, &xfer, &client_name, &name};
	for (unsigned i = 0; i < 4; ++i) {
		if (buffers[i]->data) explicit_bzero(buffers[i]->data, buffers[i]->size);
		free_buffer(buffers[i]);
	}
	if (client >= 0) close(client);
	if (loader >= 0) close(loader);
	if (account_lock >= 0) close(account_lock);
	return result;
}
