/* SPDX-License-Identifier: MIT
 * Read-only availability check: no loading, firmware commands or user records.
 */
#define main aura_fpc_unused_diagnostic_main
#include "aura_fpc_probe.c"
#undef main

int main(void)
{
	const char *names[] = {"keymaster", "keymaster64", "gatekeeper", "gatekeeper64"};
	struct buffer name = {.fd = -1};
	int fd = check_device("/dev/tee0", false), found = 0, result = 1;
	if (fd < 0) { perror("client"); return 1; }
	if (alloc_buffer(fd, &name, 4096)) goto done;
	for (unsigned i = 0; i < sizeof(names) / sizeof(names[0]); ++i) {
		uint32_t session;
		memset(name.data, 0, name.size);
		memcpy(name.data, names[i], strlen(names[i]));
		if (open_session(fd, &name, &session)) {
			printf("%s: unavailable (%s)\n", names[i], strerror(errno));
			continue;
		}
		printf("%s: resident service accessible; no commands sent\n", names[i]);
		if (close_session(fd, session)) { perror("close session"); goto done; }
		++found;
	}
	result = found ? 0 : 1;
done:
	free_buffer(&name);
	close(fd);
	return result;
}
