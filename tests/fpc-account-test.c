#include <assert.h>
#include "../port/aura-fingerprint/aura_fpc_account.h"
int main(void)
{
    char relative[64], absolute[128]; uint32_t uid;
    const char *id = "0123456789abcdef0123456789abcdef";
    assert(!aura_account_database("1001", "2", id, &uid, relative, sizeof(relative), absolute, sizeof(absolute)));
    assert(uid == 1001);
    assert(!strcmp(relative, "accounts/u1001-f2-0123456789abcdef0123456789abcdef.db"));
    assert(!strcmp(absolute, "/var/lib/aura/fpc-test-store/accounts/u1001-f2-0123456789abcdef0123456789abcdef.db"));
    assert(!aura_account_database("4294967294", "10", id, &uid, relative, sizeof(relative), absolute, sizeof(absolute)));
    const char *bad_uids[] = {"0", "999", "-1000", "+1000", "01000", "1000/../1001", "4294967295", "9999999999999999999999999999", ""};
    for (unsigned i = 0; i < sizeof(bad_uids)/sizeof(bad_uids[0]); ++i)
        assert(aura_account_database(bad_uids[i], "2", id, &uid, relative, sizeof(relative), absolute, sizeof(absolute)) == -1);
    const char *bad_fingers[] = {"0", "11", "-1", "01", "1x", ""};
    for (unsigned i = 0; i < sizeof(bad_fingers)/sizeof(bad_fingers[0]); ++i)
        assert(aura_account_database("1000", bad_fingers[i], id, &uid, relative, sizeof(relative), absolute, sizeof(absolute)) == -1);
    assert(aura_account_database("1000", "1", "../0123456789abcdef0123456789abcde", &uid, relative, sizeof(relative), absolute, sizeof(absolute)) == -1);
    assert(aura_account_database("1000", "1", id, &uid, relative, 2, absolute, sizeof(absolute)) == -1);
    assert(aura_account_database("1000", "1", id, &uid, relative, sizeof(relative), absolute, 2) == -1);
    puts("PASS: account database identifiers and bounds");
}
