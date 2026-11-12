/* SPDX-License-Identifier: MIT */
#ifndef AURA_FPC_ACCOUNT_H
#define AURA_FPC_ACCOUNT_H
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdbool.h>

/* Construct every path from bounded, canonical identifiers; never accept a
 * path from the caller. The caller must already have authorized the account. */
static inline int aura_account_number(const char *text, uint32_t min,
                                     uint32_t max, uint32_t *result)
{
    if (!text || !*text || !result || (*text == '0' && text[1])) return -1;
    uint32_t value = 0;
    for (const char *p = text; *p; ++p) {
        if (*p < '0' || *p > '9') return -1;
        unsigned digit = *p - '0';
        if (value > max / 10 || (value == max / 10 && digit > max % 10)) return -1;
        value = value * 10 + digit;
    }
    if (value < min) return -1;
    *result = value;
    return 0;
}

static inline int aura_account_database(const char *uid_text, const char *finger_text,
                                        const char *id, uint32_t *uid,
                                        char *relative, size_t relative_size,
                                        char *absolute, size_t absolute_size)
{
    uint32_t account, finger;
    if (!uid || !relative || !absolute || !id || strlen(id) != 32 ||
        aura_account_number(uid_text, 1000, UINT32_MAX - 1, &account) ||
        aura_account_number(finger_text, 1, 10, &finger)) return -1;
    for (unsigned i = 0; i < 32; ++i)
        if (!((id[i] >= '0' && id[i] <= '9') || (id[i] >= 'a' && id[i] <= 'f'))) return -1;
    char name[64], path[128];
    int n = snprintf(name, sizeof(name), "accounts/u%u-f%u-%s.db", account, finger, id);
    if (n < 0 || (size_t)n >= sizeof(name) || (size_t)n >= relative_size) return -1;
    n = snprintf(path, sizeof(path), "/var/lib/aura/fpc-test-store/%s", name);
    if (n < 0 || (size_t)n >= sizeof(path) || (size_t)n >= absolute_size) return -1;
    strcpy(relative, name);
    strcpy(absolute, path);
    *uid = account;
    return 0;
}
#endif
