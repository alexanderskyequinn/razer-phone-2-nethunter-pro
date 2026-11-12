#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work=/var/tmp/aura-rpmb-readonly
mkdir -p "$work"
cp -a "$project/sources/qsee-supplicant/." "$work/"
gcc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined -g -I"$work/include" "$project/tests/rpmb-readonly-test.c" "$project/port/aura-fingerprint/aura_rpmb_readonly.c" -Wl,--wrap=open,--wrap=close,--wrap=ioctl -o /var/tmp/aura-rpmb-readonly-test
/var/tmp/aura-rpmb-readonly-test
cd "$work"
python3 - <<'PY'
from pathlib import Path
p=Path('src/main.c'); s=p.read_text()
start=s.index('\t\tfor (unsigned int i = 0; i < delay'); end=s.index('\n\t}',start)
p.write_text(s[:start]+'\t\tqs_store_close(&store);\n\t\treturn 1;'+s[end:])
p=Path('src/services.c'); s=p.read_text().replace('const struct qs_service qs_builtin_services[]', 'int aura_rpmb_dispatch(struct qs_store *,void *,size_t);\n\nconst struct qs_service qs_builtin_services[]')
s=s.replace('{ QS_FS_SERVICE_ID', '{ 8192u, 20480u, aura_rpmb_dispatch, NULL },\n\t{ QS_FS_SERVICE_ID')
p.write_text(s)
PY
aarch64-linux-gnu-gcc -D_DEFAULT_SOURCE -DAURA_UFS_LIBRARY -std=c11 -Wall -Wextra -Werror -O2 -static -Iinclude src/main.c src/services.c src/path.c src/notify.c src/handle_db.c src/fs.c src/gpfs.c src/transport_qseecom.c "$project/port/aura-fingerprint/aura_rpmb_readonly.c" "$project/port/aura-fingerprint/aura_ufs_capabilities.c" -o "$project/build/kali/fingerprint-listener/aura-qsee-rpmb-readonly"
sha256sum "$project/build/kali/fingerprint-listener/aura-qsee-rpmb-readonly"
