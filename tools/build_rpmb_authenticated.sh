#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
# Build and run the read-only regression first; this prepares patched upstream.
bash "$project/tools/build_rpmb_readonly.sh"
work=/var/tmp/aura-rpmb-readonly
gcc -DAURA_RPMB_AUTHENTICATED_WRITE -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g -I"$work/include" "$project/tests/rpmb-authenticated-test.c" "$project/port/aura-fingerprint/aura_rpmb_readonly.c" -Wl,--wrap=open,--wrap=close,--wrap=ioctl -o /var/tmp/aura-rpmb-authenticated-test
/var/tmp/aura-rpmb-authenticated-test
cd "$work"
aarch64-linux-gnu-gcc -D_DEFAULT_SOURCE -DAURA_UFS_LIBRARY -DAURA_RPMB_AUTHENTICATED_WRITE -std=c11 -Wall -Wextra -Werror -O2 -static -Iinclude src/main.c src/services.c src/path.c src/notify.c src/handle_db.c src/fs.c src/gpfs.c src/transport_qseecom.c "$project/port/aura-fingerprint/aura_rpmb_readonly.c" "$project/port/aura-fingerprint/aura_ufs_capabilities.c" -o "$project/build/kali/fingerprint-listener/aura-qsee-rpmb-authenticated"
sha256sum "$project/build/kali/fingerprint-listener/aura-qsee-rpmb-authenticated"
