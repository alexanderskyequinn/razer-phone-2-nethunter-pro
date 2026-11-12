/* SPDX-License-Identifier: MIT
 * Link-wrapped kernel boundary: no real device opens or firmware execution.
 */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/tee.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/file.h>
#include <signal.h>
#include <unistd.h>

static struct { bool open; size_t size; unsigned char *data; int owner; } slots[32];
static int next_fd = 12;
static bool load_session, client_session, km_session;
static unsigned invokes;
static unsigned reads;
static bool handle_saved;
static bool group_selected;
static unsigned verification_challenges, random_calls;
static bool verification_setup_failed;
static unsigned account_step;
static bool account_failed, account_saved;
static unsigned account_uid(void) { return getenv("AURA_MOCK_UID") ? 1000 : 1001; }

static bool gatekeeper_test(void)
{
	const char *value = getenv("AURA_MOCK");
	return value && !strncmp(value, "gkauth-", 7);
}

ssize_t __wrap_write(int fd, const void *data, size_t size)
{
	assert(gatekeeper_test() && fd == 8 && slots[fd].open && size == 58);
	const unsigned char *p = data;
	for (size_t i = 0; i < size; ++i) assert(p[i] == 0x33);
	handle_saved = true;
	return size;
}

int __wrap_fsync(int fd)
{
	assert(fd == 8 && slots[fd].open && handle_saved);
	return 0;
}

unsigned __wrap_sleep(unsigned seconds)
{
	assert(seconds == 60 && invokes == 2);
	return 0;
}

static bool scenario(const char *name)
{
	const char *value = getenv("AURA_MOCK");
	return value && !strcmp(value, name);
}

static bool bio_test(void)
{
	const char *value = getenv("AURA_MOCK");
	return getenv("AURA_MOCK_ENROLL") || (value && !strncmp(value, "bio2-", 5));
}

ssize_t __wrap_getrandom(void *buffer, size_t size, unsigned flags)
{
	assert(bio_test() && group_selected && invokes == 4 && !flags && size && size <= 8);
	++random_calls;
	if (scenario("bio2-random-fail")) { verification_setup_failed = true; errno = EIO; return -1; }
	if (scenario("bio2-random-interrupt") && random_calls == 1) { errno = EINTR; return -1; }
	if (scenario("bio2-random-short") && size > 3) size = 3;
	memset(buffer, 0x42, size);
	return size;
}

int __wrap_lstat(const char *path, struct stat *st)
{
	assert(bio_test());
	memset(st, 0, sizeof(*st));
	if (getenv("AURA_MOCK_ACCOUNT")) {
		const char *db = account_uid() == 1000 ? "/var/lib/aura/fpc-test-store/accounts/u1000-f2-0123456789abcdef0123456789abcdef.db" : "/var/lib/aura/fpc-test-store/accounts/u1001-f2-0123456789abcdef0123456789abcdef.db";
		if (strcmp(path, db)) {
			assert(!strcmp(path, "/var") || !strcmp(path, "/var/lib") || !strcmp(path, "/var/lib/aura") ||
			       !strcmp(path, "/var/lib/aura/fpc-test-store") || !strcmp(path, "/var/lib/aura/fpc-test-store/accounts"));
			st->st_mode = S_IFDIR | 0700;
			if (getenv("AURA_MOCK_UNSAFE_PARENT")) st->st_mode |= 0020;
			return 0;
		}
	} else assert(!strcmp(path, "/var/lib/aura/fpc-test-store/aura-fpc-test.db"));
	if (strstr(getenv("AURA_MOCK"), "enroll") && !scenario("bio2-enroll-existing") && !scenario("account-enroll-existing")) {
		errno = ENOENT; return -1;
	}
	st->st_mode = S_IFREG | 0600; st->st_size = 1024; st->st_nlink = 1;
	return 0;
}

int __real_fstat(int fd, struct stat *st);
int __wrap_fstat(int fd, struct stat *st)
{
	if (fd == 8 && getenv("AURA_MOCK_ENROLL")) {
		assert(slots[fd].open);
		memset(st, 0, sizeof(*st)); st->st_mode = S_IFREG | 0600; st->st_size = 58; st->st_nlink = 1;
		if (scenario("account-enroll-unsafe-handle")) st->st_nlink = 2;
		return 0;
	}
	if (fd != 7) return __real_fstat(fd, st);
	assert(getenv("AURA_MOCK_ACCOUNT") && slots[7].open);
	memset(st, 0, sizeof(*st)); st->st_mode = S_IFREG | 0600; st->st_nlink = 1;
	return 0;
}

int __wrap_flock(int fd, int operation)
{
	assert(fd == 7 && slots[7].open && operation == (LOCK_EX | LOCK_NB));
	if (getenv("AURA_MOCK_LOCK_BUSY")) { errno = EWOULDBLOCK; return -1; }
	return 0;
}

off_t __wrap_lseek(int fd, off_t offset, int whence)
{
	assert(fd == 9 && slots[fd].open && offset == 0 && whence == SEEK_SET);
	return 0;
}

ssize_t __real_read(int fd, void *data, size_t size);
ssize_t __wrap_read(int fd, void *data, size_t size)
{
	if (fd == 0) return __real_read(fd, data, size);
	if (fd == 8 && getenv("AURA_MOCK_ENROLL")) {
		assert(slots[fd].open && size == 58); memset(data, 0x33, size); return size;
	}
	assert(fd == 9 && slots[fd].open && size == 2 && invokes >= 2 && (bio_test() || !(invokes % 2)));
	char *p = data;
	p[0] = (scenario("account-enroll-cancel") || scenario("bio2-enroll-cancel") || scenario("bio2-verify-cancel")) ? '0' : bio_test() ? '1' : (!reads++ || scenario("capture-timeout")) ? '0' : '1';
	p[1] = '\n';
	return 2;
}

int __wrap_usleep(useconds_t duration)
{
	assert(duration == 100000 && (bio_test() || invokes == 2));
	if (scenario("bio2-enroll-cancel") || scenario("bio2-verify-cancel") || scenario("account-enroll-cancel")) { account_failed = true; raise(SIGTERM); }
	return 0;
}

int __wrap_open(const char *path, int flags, ...)
{
	int fd;
	(void)flags;
	if (getenv("AURA_MOCK_ENROLL") && strstr(path, "gatekeeper.handle")) {
		assert(!strcmp(path, account_uid() == 1000 ? "/var/lib/aura/fpc-test-store/kali-gatekeeper.handle" : "/var/lib/aura/fpc-test-store/accounts/u1001-gatekeeper.handle"));
		assert(!(flags & (O_WRONLY | O_CREAT)) && (flags & O_NOFOLLOW));
		if (scenario("account-enroll-missing-handle")) { account_failed = true; errno = ENOENT; return -1; }
		if (scenario("account-enroll-unsafe-handle")) account_failed = true;
		assert(!slots[8].open); slots[8].open = true; return 8;
	}
	if (gatekeeper_test() && !strcmp(path, "/var/lib/aura/fpc-test-store/kali-gatekeeper.handle")) {
		if (!(flags & O_WRONLY)) { errno = ENOENT; return -1; }
		assert((flags & O_EXCL) && (flags & O_NOFOLLOW) && !slots[8].open);
		slots[8].open = true;
		return 8;
	}
	if (!strcmp(path, "/run/aura-fpc-test.lock")) { assert(getenv("AURA_MOCK_ACCOUNT")); fd = 7; }
	else if (!strcmp(path, "/sys/bus/platform/devices/fingerprint/irq")) fd = 9;
	else if (!strcmp(path, "/dev/tee0")) fd = 10;
	else { assert(!strcmp(path, "/dev/teepriv0")); fd = 11; }
	assert(!slots[fd].open);
	slots[fd].open = true;
	return fd;
}

int __wrap_close(int fd)
{
	assert(fd >= 7 && fd < 32 && slots[fd].open);
	assert(!slots[fd].data);
	slots[fd].open = false;
	return 0;
}

void *__wrap_mmap(void *addr, size_t size, int prot, int flags, int fd, off_t off)
{
	(void)addr; (void)prot; (void)flags;
	assert(fd >= 12 && fd < 32 && slots[fd].open && !off);
	assert(size == slots[fd].size && !slots[fd].data);
	if (scenario("mmap-fail")) { errno = ENOMEM; return MAP_FAILED; }
	slots[fd].data = calloc(1, size);
	assert(slots[fd].data);
	return slots[fd].data;
}

int __wrap_munmap(void *addr, size_t size)
{
	for (int fd = 12; fd < next_fd; ++fd) {
		if (slots[fd].data == addr) {
			assert(size == slots[fd].size);
			free(addr);
			slots[fd].data = NULL;
			return 0;
		}
	}
	abort();
}

static unsigned char *resolve(int owner, struct tee_ioctl_param *p)
{
	assert(p->c >= 12 && p->c < 32);
	assert(slots[p->c].owner == owner && slots[p->c].data);
	assert(p->a <= slots[p->c].size && p->b <= slots[p->c].size - p->a);
	return slots[p->c].data + p->a;
}

#include "fpc-account-enroll-mock.inc"

int __wrap_ioctl(int fd, unsigned long cmd, ...)
{
	va_list ap;
	void *data;
	assert(fd == 10 || fd == 11);
	assert(slots[fd].open);
	va_start(ap, cmd);
	data = va_arg(ap, void *);
	va_end(ap);
	if (cmd == TEE_IOC_VERSION) {
		struct tee_ioctl_version_data *v = data;
		v->impl_id = scenario("wrong-driver") ? 1 : 5;
		v->gen_caps = fd == 11 ? TEE_GEN_CAP_PRIVILEGED : 0;
		return 0;
	}
	if (cmd == TEE_IOC_SHM_ALLOC) {
		struct tee_ioctl_shm_alloc_data *a = data;
		assert(!a->flags && a->size == 4096);
		if (scenario("alloc-fail")) { errno = ENOMEM; return -1; }
		assert(next_fd < 32);
		a->id = next_fd;
		slots[next_fd].size = a->size;
		slots[next_fd].owner = fd;
		slots[next_fd].open = true;
		return next_fd++;
	}
	if (cmd == TEE_IOC_OPEN_SESSION) {
		struct tee_ioctl_buf_data *b = data;
		struct tee_ioctl_open_session_arg *a = (void *)(uintptr_t)b->buf_ptr;
		assert(b->buf_len == sizeof(*a) + sizeof(struct tee_ioctl_param));
		assert(a->num_params == 1 && !a->clnt_login && !a->cancel_id);
		for (size_t i = 0; i < 16; ++i) assert(!a->uuid[i] && !a->clnt_uuid[i]);
		assert(a->params[0].attr == TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT);
		assert(a->params[0].b == sizeof("fpctzappfingerprint"));
		if (!strcmp((char *)resolve(fd, &a->params[0]), "keymaster64")) {
			assert(fd == 10 && client_session && !km_session);
			km_session = true; a->session = 81; return 0;
		}
		assert(!memcmp(resolve(fd, &a->params[0]), "fpctzappfingerprint", a->params[0].b));
		if ((fd == 11 && scenario("load-fail")) || (fd == 10 && scenario("session-fail"))) {
			errno = EIO; return -1;
		}
		if (fd == 11) { assert(!load_session); load_session = true; a->session = 70; }
		else { assert(load_session && !client_session); client_session = true; a->session = 80; }
		return 0;
	}
	if (cmd == TEE_IOC_INVOKE) {
		struct tee_ioctl_buf_data *b = data;
		struct tee_ioctl_invoke_arg *a = (void *)(uintptr_t)b->buf_ptr;
		unsigned char *request, *response, *shared;
		const unsigned char prefix[] = {9,0,0,0,2,0,0,0,255,255,255,255,0,4,0,0};
		bool detect = scenario("finger-detect") || scenario("finger-arm-fail");
		bool retry = scenario("capture-retry") || scenario("capture-exhausted");
		bool bio = scenario("bio-preflight") || scenario("bio-nonempty") || scenario("bio-bad-count") || scenario("bio-begin-reject");
		bool auth = gatekeeper_test() || (getenv("AURA_MOCK") && !strncmp(getenv("AURA_MOCK"), "auth-", 5));
		bool capture = retry || scenario("capture") || scenario("capture-fail") || scenario("capture-timeout");
		unsigned index = invokes++;
		assert(fd == 10 && load_session && client_session);
		if (getenv("AURA_MOCK_ENROLL")) return account_enroll_invoke(fd, a);
		if (gatekeeper_test() && (index == 3 || index == 4)) {
			assert(km_session && a->session == 81 && a->num_params == 2);
			assert(a->params[0].b == (index == 3 ? 4 : 24) && a->params[1].b == 3072);
			request = resolve(fd, &a->params[0]); response = resolve(fd, &a->params[1]);
			assert(request[0] == (index == 3 ? 0 : 7) && request[1] == 2);
			memset(response, 0, 3072);
			if (index == 3) { response[4] = 4; response[8] = 5; response[12] = 4; response[16] = 5; }
			else {
				assert(request[4] == 4 && request[8] == 5 && request[12] == 4 && request[16] == 5 && !request[20]);
				if (scenario("gkauth-version-reject")) memset(response, 255, 4);
			}
			return 0;
		}
		if (gatekeeper_test() && (index == 5 || index == 6)) {
			assert(km_session && a->session == 81 && !a->func && a->num_params == 2);
			assert(a->params[0].b == (index == 5 ? 36 : 94) && a->params[1].b == 3072);
			request = resolve(fd, &a->params[0]); response = resolve(fd, &a->params[1]);
			assert(request[0] == (index == 5 ? 1 : 2) && request[1] == 16);
			assert(request[4] == 0xe8 && request[5] == 3);
			memset(response, 0, 3072); response[4] = 12;
			if (index == 5) {
				assert(request[24] == 32 && request[28] == 4 && !memcmp(request + 32, "2468", 4));
				response[8] = 58; memset(response + 12, 0x33, 58);
				if (scenario("gkauth-enroll-reject")) memset(response, 255, 4);
			} else {
				assert(handle_saved && request[8] == 42 && request[16] == 32 && request[20] == 58);
				assert(request[24] == 90 && request[28] == 4 && !memcmp(request + 90, "2468", 4));
				response[8] = 69; response[13] = scenario("gkauth-wrong-challenge") ? 43 : 42;
				memset(response + 49, 0x55, 32);
			}
			return 0;
		}
		if (auth && index == 0) {
			assert(km_session && a->session == 81 && !a->func && a->num_params == 2);
			assert(b->buf_len == sizeof(*a) + 2 * sizeof(struct tee_ioctl_param));
			assert(a->params[0].attr == TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT && a->params[0].b == 64);
			assert(a->params[1].attr == TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_OUTPUT && a->params[1].b == 960);
			request = resolve(fd, &a->params[0]); response = resolve(fd, &a->params[1]);
			assert(request[0] == 5 && request[1] == 2 && request[4] == 2);
			for (unsigned i = 8; i < 64; ++i) assert(!request[i]);
			memset(response, 0, 960);
			response[4] = 12; response[8] = 16;
			memset(response + 12, 0x42, 16);
			if (scenario("auth-key-reject")) memset(response, 255, 4);
			if (scenario("auth-bad-bounds")) memset(response + 4, 255, 4);
			return 0;
		}
		assert(gatekeeper_test() ? (index == 1 || index == 2 || index == 7) : auth ? index == 1 : bio_test() ? index < 64 : bio ? index < 4 : retry ? index < 22 : capture ? index < 4 : detect ? index < 3 : index == 0);
		assert(b->buf_len == sizeof(*a) + 4 * sizeof(struct tee_ioctl_param));
		assert(!a->func && a->session == 80 && a->num_params == 4);
		assert(a->params[0].attr == TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT && a->params[0].b == 64);
		assert(a->params[1].attr == TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_OUTPUT && a->params[1].b == 64);
		assert(a->params[2].attr == TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INPUT);
		assert(a->params[2].a == 4 && a->params[2].b == 4 && !a->params[2].c);
		assert(a->params[3].attr == TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INOUT && a->params[3].b == 4096);
		request = resolve(fd, &a->params[0]); response = resolve(fd, &a->params[1]);
		shared = resolve(fd, &a->params[3]);
		assert(request[0] == 0 && request[1] == 16 && !request[2] && !request[3]);
		for (size_t i = 4; i < 64; ++i) assert(!request[i]);
		if (gatekeeper_test() && index == 2) {
			assert(shared[0] == 3 && shared[4] == 2);
			memset(response, 0, 64); memset(shared + 16, 0, 4); shared[8] = 42;
			return 0;
		}
		if (gatekeeper_test() && index == 7) {
			assert(shared[0] == 3 && shared[4] == 3 && shared[12] == 69 && shared[17] == 42);
			memset(response, 0, 64); memset(shared + 8, scenario("gkauth-fpc-reject") ? 255 : 0, 4);
			return 0;
		}
		if (auth) {
			assert(shared[0] == 3 && shared[4] == 5 && shared[12] == 16);
			for (unsigned i = 16; i < 32; ++i) assert(shared[i] == 0x42);
			memset(response, 0, 64);
			memset(shared + 8, scenario("auth-fpc-reject") ? 255 : 0, 4);
			return 0;
		}
		if (bio_test()) {
			if (shared[0] == 3 && shared[4] == 1) {
				assert(group_selected && index == 4 && !verification_challenges);
				for (unsigned n = 8; n < 16; ++n) assert(shared[n] == 0x42);
				for (unsigned n = 16; n < 20; ++n) assert(shared[n] == 255);
				for (unsigned n = 20; n < 4096; ++n) assert(!shared[n]);
				++verification_challenges;
				--invokes; /* Existing sequence indices exclude the setup command. */
				verification_setup_failed = scenario("bio2-challenge-reject");
				memset(response, 0, 64);
				memset(shared + 16, verification_setup_failed ? 255 : 0, 4);
				return 0;
			}
			bool enrollment = strstr(getenv("AURA_MOCK"), "enroll") != NULL;
			bool check = strstr(getenv("AURA_MOCK"), "bio2-check") != NULL;
			bool soft_capture = scenario("bio2-enroll-capture1") || scenario("bio2-enroll-capture4");
			unsigned step = soft_capture && index >= 9 ? index - 4 : index;
			bool verify_quality = scenario("bio2-quality-retry") || scenario("bio2-quality-exhausted");
			if (verify_quality && index >= 4)
				step = scenario("bio2-quality-exhausted") && index == 54 ? 8 :
				       scenario("bio2-quality-retry") && index >= 9 ? index - 5 : 4 + (index - 4) % 5;
			if (check) step = index + 1; /* No sensor commands in reload-only mode. */
			bool exhausted_capture = scenario("bio2-enroll-capture-exhausted");
			if (exhausted_capture && index >= 7)
				step = index >= 27 ? index - 22 : index % 2 ? 7 : 6;
			static const unsigned char enroll_ops[][2] = {
				{10,4},{11,7},{3,2},{11,6},{11,0},
				{10,0},{10,2},{10,3},{11,1},
				{10,0},{10,2},{10,3},{11,1},
				{11,2},{11,7},{2,12},{10,4}};
			static const unsigned char verify_ops[][2] = {
				{10,4},{2,11},{11,9},{11,7},{10,0},{10,2},{10,3},{11,3},{10,4}};
			unsigned module = shared[0], command = shared[4];
			bool rejected = (verification_setup_failed && index == 4) || (scenario("bio2-enroll-reject") && index == 9) ||
				(scenario("bio2-load-fail") && index == 2) ||
				(scenario("bio2-group-fail") && index == 3);
			const unsigned char *op = enrollment ? enroll_ops[step] : verify_ops[step];
			bool soft_idle = (soft_capture && index == 8) || (scenario("bio2-enroll-cancel") && index >= 7) || (scenario("bio2-verify-cancel") && index >= 6) || (exhausted_capture && index == 26);
			assert(module == (rejected || soft_idle ? 10 : op[0]) && command == (rejected || soft_idle ? 4 : op[1]));
			unsigned offset = module == 3 ? 16 : 8;
			for (unsigned n = 0; n < 4; ++n) assert(shared[offset+n] == 255);
			memset(response, 0, 64); memset(shared + offset, 0, 4);
			if (module == 3) shared[8] = 42;
			if (module == 10 && command == 0) shared[8] = 1;
			if (soft_capture && index == 7) shared[8] = scenario("bio2-enroll-capture1") ? 1 : 4;
			if (exhausted_capture && index >= 7 && index <= 25 && index % 2) shared[8] = 3;
			if (module == 11 && command == 9) {
				assert(shared[12] == (getenv("AURA_MOCK_ACCOUNT") ? 0xe9 : 0xe8) && shared[13] == 3 && !shared[14] && !shared[15]);
				group_selected = true;
				if (scenario("bio2-group-fail")) memset(shared + 8, 255, 4);
			}
			if (module == 11 && command == 7) {
				assert(shared[12] == 5);
				if (!enrollment) assert(group_selected);
				shared[12] = enrollment && index == 1 ? 0 : 1;
				if (scenario("bio2-check-empty")) shared[12] = 0;
				shared[16] = 73;
			}
			if (module == 11 && command == 1) {
				shared[8] = step == 8 ? (scenario("bio2-enroll-reject") ? 2 : 1) : 0;
				shared[12] = step == 8 ? 1 : 0;
			}
			if (module == 11 && command == 2) shared[12] = 73;
			if (module == 11 && command == 3)
				shared[12] = scenario("bio2-no-match") ? 0 : scenario("bio2-wrong-id") ? 74 : 73;
			if (module == 11 && command == 3 && verify_quality &&
			    (scenario("bio2-quality-exhausted") || index == 7)) shared[8] = 2;
			if (module == 2) {
				const char *expected_name = getenv("AURA_MOCK_ACCOUNT") ? "accounts/u1001-f2-0123456789abcdef0123456789abcdef.db" : "aura-fpc-test.db";
				assert(shared[12] == strlen(expected_name) + 1);
				assert(!strcmp((char *)shared + 16, expected_name));
				if (scenario("bio2-load-fail")) memset(shared + 8, 255, 4);
			}
			return 0;
		}
		if (bio) {
			static const unsigned char commands[][2] = {{11,7},{3,2},{11,6},{11,0}};
			unsigned offset = index == 1 ? 16 : 8;
			assert(shared[0] == commands[index][0] && shared[4] == commands[index][1]);
			for (unsigned i = 1; i < 4; ++i) assert(!shared[i] && !shared[i+4]);
			for (unsigned i = 0; i < 4; ++i) assert(shared[offset+i] == 255);
			if (index == 0) assert(shared[12] == 5);
			memset(response, 0, 64);
			memset(shared + offset, 0, 4);
			if (index == 0) shared[12] = scenario("bio-nonempty") ? 1 : scenario("bio-bad-count") ? 6 : 0;
			if (index == 1) shared[8] = 42;
			if (index == 3 && scenario("bio-begin-reject")) memset(shared + 8, 255, 4);
			return 0;
		}
		if (capture || detect || scenario("sensor-init") || scenario("sensor-fail") || scenario("sensor-no-reply")) {
			unsigned char sensor_prefix[] = {10,0,0,0,4,0,0,0,255,255,255,255};
			if ((capture || detect) && index == 1) sensor_prefix[4] = 2;
			if (capture && index == 2 && !scenario("capture-timeout")) sensor_prefix[4] = 3;
			if (retry) {
				unsigned last = scenario("capture-retry") ? 5 : 21;
				sensor_prefix[4] = index == 0 || index == last ? 4 : index % 2 ? 2 : 3;
			}
			assert(!memcmp(shared, sensor_prefix, sizeof(sensor_prefix)));
			for (size_t i = sizeof(sensor_prefix); i < 4096; ++i) assert(!shared[i]);
			memset(response, 0, 64);
			if (!scenario("sensor-no-reply")) memset(shared + 8, scenario("sensor-fail") ? 255 : 0, 4);
			if (scenario("finger-arm-fail") && index == 1) memset(shared + 8, 255, 4);
			if (scenario("capture-fail") && index == 2) shared[8] = 3;
			if ((scenario("capture-retry") && index == 2) ||
			    (scenario("capture-exhausted") && sensor_prefix[4] == 3)) shared[8] = 3;
			return 0;
		}
		assert(!memcmp(shared, prefix, sizeof(prefix)));
		if (scenario("invoke-fail")) { errno = EIO; return -1; }
		if (!scenario("bad-response")) memset(response, 0, 64);
		memset(shared + 8, 0, 4);
		memcpy(shared + 16, "mock firmware\nversion 1", 24);
		return 0;
	}
	if (cmd == TEE_IOC_CLOSE_SESSION) {
		struct tee_ioctl_close_session_arg *a = data;
		if (fd == 10 && a->session == 81) { assert(km_session); km_session = false; return 0; }
		if (fd == 10) { assert(client_session && a->session == 80); client_session = false; }
		else { assert(load_session && !client_session && a->session == 70); load_session = false; }
		if (scenario("close-fail") || (fd == 10 && scenario("account-enroll-close-fail"))) { errno = EIO; return -1; }
		return 0;
	}
	abort();
}

__attribute__((destructor)) static void check_cleanup(void)
{
	assert(!load_session && !client_session && !km_session);
	if (getenv("AURA_MOCK_ENROLL")) {
		assert(!handle_saved);
		if (scenario("account-enroll-good") || scenario("account-enroll-close-fail")) assert(account_saved && account_step == 20);
		else assert(!account_saved);
	}
	if (scenario("gkauth-good") || scenario("gkauth-fpc-reject")) assert(invokes == 8 && handle_saved);
	if (scenario("gkauth-enroll-reject")) assert(invokes == 6 && !handle_saved);
	if (scenario("gkauth-version-reject")) assert(invokes == 5 && !handle_saved);
	if (scenario("gkauth-wrong-challenge")) assert(invokes == 7 && handle_saved);
	if (scenario("auth-good") || scenario("auth-fpc-reject")) assert(invokes == 2);
	if (scenario("auth-key-reject") || scenario("auth-bad-bounds")) assert(invokes == 1);
	if (scenario("finger-detect") || scenario("finger-arm-fail")) assert(invokes == 3);
	if (scenario("capture") || scenario("capture-fail")) assert(invokes == 4 && reads == 2);
	if (scenario("capture-timeout")) assert(invokes == 3 && reads == 600);
	if (scenario("capture-retry")) assert(invokes == 6 && reads == 3);
	if (scenario("capture-exhausted")) assert(invokes == 22 && reads == 11);
	if (scenario("bio-preflight") || scenario("bio-begin-reject")) assert(invokes == 4);
	if (scenario("bio-nonempty") || scenario("bio-bad-count")) assert(invokes == 1);
	if (scenario("bio2-enroll")) assert(invokes == 17);
	if (scenario("bio2-enroll-cancel")) assert(invokes == 9);
	if (scenario("bio2-verify-cancel")) assert(invokes == 8);
	if (scenario("bio2-enroll-capture-exhausted")) assert(invokes == 39);
	if (scenario("bio2-enroll-capture1") || scenario("bio2-enroll-capture4")) assert(invokes == 21);
	if (scenario("bio2-enroll-reject")) assert(invokes == 10);
	if (scenario("bio2-enroll-existing")) assert(invokes == 0);
	if (scenario("bio2-match") || scenario("bio2-no-match") || scenario("bio2-wrong-id") || scenario("bio2-random-short") || scenario("bio2-random-interrupt")) assert(invokes == 9 && verification_challenges == 1);
	if (scenario("bio2-challenge-reject")) assert(invokes == 5 && verification_challenges == 1);
	if (scenario("bio2-random-fail")) assert(invokes == 5 && !verification_challenges);
	if (scenario("bio2-random-short")) assert(random_calls == 3);
	if (scenario("bio2-random-interrupt")) assert(random_calls == 2);
	if (scenario("bio2-quality-retry")) assert(invokes == 14 && verification_challenges == 1);
	if (scenario("bio2-quality-exhausted")) assert(invokes == 55 && verification_challenges == 1);
	if (scenario("bio2-load-fail")) assert(invokes == 3);
	if (scenario("bio2-group-fail")) assert(invokes == 4);
	if (scenario("bio2-check-good") || scenario("bio2-check-empty")) assert(invokes == 3);
	for (int i = 7; i < 32; ++i) assert(!slots[i].open && !slots[i].data);
}
