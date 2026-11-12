#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
target="$project/build/kali/fingerprint"
gcc -Wall -Wextra -Werror -fsanitize=address,undefined -g "$project/tests/fpc-protocol-test.c" -o /var/tmp/aura-fpc-protocol-test
/var/tmp/aura-fpc-protocol-test
gcc -Wall -Wextra -Werror -fsanitize=address,undefined -g "$project/port/aura-fingerprint/aura_fpc_probe.c" "$project/tests/fpc-probe-mock.c" -Wl,--wrap=open,--wrap=close,--wrap=ioctl,--wrap=mmap,--wrap=munmap,--wrap=sleep,--wrap=usleep,--wrap=read,--wrap=lseek -o /var/tmp/aura-fpc-probe-mock
/var/tmp/aura-fpc-probe-mock --inspect
/var/tmp/aura-fpc-probe-mock --load-build-info
AURA_MOCK=sensor-init /var/tmp/aura-fpc-probe-mock --sensor-init
AURA_MOCK=finger-detect /var/tmp/aura-fpc-probe-mock --finger-detect-test
set +e
AURA_MOCK=finger-arm-fail /var/tmp/aura-fpc-probe-mock --finger-detect-test
status=$?
set -e
test "$status" -eq 1
AURA_MOCK=capture /var/tmp/aura-fpc-probe-mock --capture-once
AURA_MOCK=capture-retry /var/tmp/aura-fpc-probe-mock --capture-test
set +e
AURA_MOCK=capture-exhausted /var/tmp/aura-fpc-probe-mock --capture-test
status=$?
set -e
test "$status" -eq 1
for scenario in capture-fail capture-timeout; do
    set +e
    AURA_MOCK="$scenario" /var/tmp/aura-fpc-probe-mock --capture-once
    status=$?
    set -e
    test "$status" -eq 1
done
for scenario in sensor-fail sensor-no-reply; do
    set +e
    AURA_MOCK="$scenario" /var/tmp/aura-fpc-probe-mock --sensor-init
    status=$?
    set -e
    test "$status" -eq 1
done
for scenario in wrong-driver alloc-fail mmap-fail load-fail session-fail invoke-fail bad-response close-fail; do
    set +e
    AURA_MOCK="$scenario" /var/tmp/aura-fpc-probe-mock --load-build-info
    status=$?
    set -e
    if [ "$status" -ne 1 ]; then
        printf 'Unexpected exit %s for %s\n' "$status" "$scenario" >&2
        exit 1
    fi
done
printf 'Mock TEE transport and eight failure cleanup tests passed\n'
aarch64-linux-gnu-gcc -Wall -Wextra -Werror -O2 -static "$project/port/aura-fingerprint/aura_fpc_probe.c" -o "$target/aura-fpc-probe"
file "$target/aura-fpc-probe"
sha256sum "$target/aura-fpc-probe"
