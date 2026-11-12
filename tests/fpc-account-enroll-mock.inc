/* Synthetic protocol state machine: no secure hardware or private state. */
static uint32_t account_word(const unsigned char *p)
{
	return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static int account_enroll_invoke(int fd, struct tee_ioctl_invoke_arg *a)
{
	unsigned step = account_step++;
	assert(!a->func);
	unsigned char *request = resolve(fd, &a->params[0]);
	unsigned char *response = resolve(fd, &a->params[1]);
	if (a->session == 81) {
		assert(km_session && a->num_params == 2 && !account_failed);
		unsigned command = account_word(request);
		assert(command != 0x1001); /* Provisioning is forbidden in account mode. */
		memset(response, 0, a->params[1].b);
		if (step == 4) {
			assert(command == 0x205 && account_word(request + 4) == 2);
			response[4] = 12; response[8] = 16; memset(response + 12, 0x42, 16);
		} else if (step == 7) {
			assert(command == 0x200); response[4] = 4; response[8] = 5; response[12] = 4; response[16] = 5;
		} else if (step == 8) {
			assert(command == 0x207 && a->params[0].b == 24);
		} else {
			assert(step == 9 && command == 0x1002 && a->params[0].b == 94);
			assert(account_word(request + 4) == account_uid());
			assert(account_word(request + 8) == 42 && account_word(request + 16) == 32 && account_word(request + 20) == 58);
			for (unsigned i = 32; i < 90; ++i) assert(request[i] == 0x33);
			assert(account_word(request + 24) == 90 && account_word(request + 28) == 4 && !memcmp(request + 90, "2468", 4));
			response[4] = 12; response[8] = 69; response[13] = 42;
			memset(response + 49, 0x55, 32);
			if (scenario("account-enroll-wrong-pin")) { memset(response, 255, 4); account_failed = true; }
			if (scenario("account-enroll-throttled")) { response[0] = 30; account_failed = true; }
			if (scenario("account-enroll-stale-token")) { response[13] = 43; account_failed = true; }
		}
		return 0;
	}
	assert(a->session == 80 && a->num_params == 4);
	unsigned char *shared = resolve(fd, &a->params[3]);
	unsigned module = account_word(shared), command = account_word(shared + 4);
	static const unsigned char ops[][2] = {
		{10,4}, {11,7}, {11,6}, {11,9}, {0,0}, {3,5}, {3,2}, {0,0}, {0,0}, {0,0},
		{3,3}, {11,0}, {10,0}, {10,2}, {10,3}, {11,1}, {11,2}, {11,7}, {2,12}, {10,4}
	};
	if (account_failed) assert(module == 10 && command == 4);
	else assert(step < 20 && module == ops[step][0] && command == ops[step][1]);
	memset(response, 0, 64);
	memset(shared + (module == 3 && command == 2 ? 16 : 8), 0, 4);
	if (module == 11 && command == 7) { shared[12] = step == 1 ? 0 : 1; shared[16] = 73; }
	if (module == 11 && command == 9) assert(account_word(shared + 12) == account_uid());
	if (module == 3 && command == 5) assert(shared[12] == 16 && shared[16] == 0x42);
	if (module == 3 && command == 2) shared[8] = 42;
	if (module == 3 && command == 3) {
		assert(shared[12] == 69 && shared[17] == 42);
		if (scenario("account-enroll-token-reject")) { memset(shared + 8, 255, 4); account_failed = true; }
	}
	if (module == 10 && command == 0) shared[8] = 1;
	if (module == 11 && command == 1) shared[12] = 0;
	if (module == 11 && command == 2) shared[12] = 73;
	if (module == 2) {
		char expected[80];
		snprintf(expected, sizeof(expected), "accounts/u%u-f2-0123456789abcdef0123456789abcdef.db", account_uid());
		assert(!strcmp((char *)shared + 16, expected));
		if (scenario("account-enroll-save-fail")) { memset(shared + 8, 255, 4); account_failed = true; }
		else account_saved = true;
	}
	return 0;
}
