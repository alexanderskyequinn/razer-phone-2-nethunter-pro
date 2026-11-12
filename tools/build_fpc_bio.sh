#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
gcc -Wall -Wextra -Werror -fsanitize=address,undefined -g "$project/tests/gatekeeper-protocol-test.c" -o /var/tmp/aura-gatekeeper-protocol-test
/var/tmp/aura-gatekeeper-protocol-test
gcc -Wall -Wextra -Werror -fsanitize=address,undefined -g "$project/port/aura-fingerprint/aura_fpc_bio.c" "$project/tests/fpc-probe-mock.c" -Wl,--wrap=open,--wrap=close,--wrap=ioctl,--wrap=mmap,--wrap=munmap,--wrap=sleep,--wrap=usleep,--wrap=read,--wrap=lseek,--wrap=lstat,--wrap=fstat,--wrap=flock,--wrap=write,--wrap=fsync,--wrap=getrandom -o /var/tmp/aura-fpc-bio-mock
AURA_MOCK=bio-preflight /var/tmp/aura-fpc-bio-mock --enrollment-preflight
for scenario in bio-nonempty bio-bad-count bio-begin-reject; do
    set +e
    AURA_MOCK="$scenario" /var/tmp/aura-fpc-bio-mock --enrollment-preflight
    result=$?
    set -e
    test "$result" -eq 1
done
for scenario in bio2-enroll bio2-enroll-cancel bio2-enroll-capture1 bio2-enroll-capture4 bio2-enroll-capture-exhausted bio2-enroll-reject bio2-enroll-existing bio2-match bio2-no-match bio2-wrong-id bio2-load-fail bio2-group-fail bio2-check-good bio2-check-empty; do
    mode=--verify-test
    expected=1
    case "$scenario" in *enroll*) mode=--enroll-test;; esac
    case "$scenario" in bio2-check*) mode=--check-database;; esac
    case "$scenario" in bio2-enroll|bio2-enroll-capture*|bio2-match|bio2-check-good) expected=0;; bio2-no-match) expected=3;; esac
    set +e
    AURA_MOCK="$scenario" /var/tmp/aura-fpc-bio-mock "$mode"
    result=$?
    set -e
    test "$result" -eq "$expected"
done
aarch64-linux-gnu-gcc -Wall -Wextra -Werror -O2 -static "$project/port/aura-fingerprint/aura_fpc_bio.c" -o "$project/build/kali/fingerprint/aura-fpc-bio"
for scenario in auth-good auth-key-reject auth-bad-bounds auth-fpc-reject; do
    expected=1
    test "$scenario" != auth-good || expected=0
    set +e
    AURA_MOCK="$scenario" /var/tmp/aura-fpc-bio-mock --auth-preflight
    result=$?
    set -e
    test "$result" -eq "$expected"
done
for scenario in gkauth-good gkauth-version-reject gkauth-enroll-reject gkauth-wrong-challenge gkauth-fpc-reject; do
    expected=1
    test "$scenario" != gkauth-good || expected=0
    set +e
    AURA_MOCK="$scenario" /var/tmp/aura-fpc-bio-mock --authorization-test <<<2468
    result=$?
    set -e
    test "$result" -eq "$expected"
done
gcc -Wall -Wextra -Werror -fsanitize=address,undefined -g "$project/tests/fpc-account-test.c" -o /var/tmp/aura-fpc-account-test
/var/tmp/aura-fpc-account-test
for scenario in bio2-match bio2-no-match bio2-wrong-id bio2-load-fail bio2-group-fail bio2-check-good bio2-check-empty bio2-verify-cancel bio2-challenge-reject bio2-random-fail bio2-random-short bio2-random-interrupt bio2-quality-retry bio2-quality-exhausted; do
    mode=--account-verify
    expected=1
    case "$scenario" in bio2-check*) mode=--account-check;; esac
    case "$scenario" in bio2-match|bio2-check-good|bio2-random-short|bio2-random-interrupt|bio2-quality-retry) expected=0;; bio2-no-match) expected=3;; bio2-verify-cancel) expected=4;; bio2-quality-exhausted) expected=5;; esac
    set +e
    AURA_MOCK="$scenario" AURA_MOCK_ACCOUNT=1 /var/tmp/aura-fpc-bio-mock "$mode" 1001 2 0123456789abcdef0123456789abcdef
    result=$?
    set -e
    test "$result" -eq "$expected"
done
set +e
AURA_MOCK=bio2-account-invalid AURA_MOCK_ACCOUNT=1 AURA_MOCK_LOCK_BUSY=1 /var/tmp/aura-fpc-bio-mock --account-verify 1001 2 0123456789abcdef0123456789abcdef
result=$?
set -e
test "$result" -eq 5
set +e
AURA_MOCK=bio2-account-invalid AURA_MOCK_ACCOUNT=1 AURA_MOCK_UNSAFE_PARENT=1 /var/tmp/aura-fpc-bio-mock --account-verify 1001 2 0123456789abcdef0123456789abcdef
result=$?
set -e
test "$result" -eq 1
python3 -B "$project/tests/test_fpc_account_enroll.py"
sha256sum "$project/build/kali/fingerprint/aura-fpc-bio"
