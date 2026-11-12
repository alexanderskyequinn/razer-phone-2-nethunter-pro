#!/bin/bash
set -euo pipefail
project=$(cd "$(dirname "$0")/.." && pwd)
work=/var/tmp/aura-qsee-supplicant-test
mkdir -p "$work" "$project/build/kali/fingerprint-listener"
cp -a "$project/sources/qsee-supplicant/." "$work/"
cd "$work"
python3 - <<'PY'
from pathlib import Path
p=Path('src/main.c')
s=p.read_text()
start=s.index('\t\tfor (unsigned int i = 0; i < delay')
end=s.index('\n\t}',start)
s=s[:start]+'\t\t/* Bring-up: do not re-register after an uncertain transport failure. */\n\t\tqs_store_close(&store);\n\t\treturn 1;'+s[end:]
p.write_text(s)
PY
make check CFLAGS='-std=c11 -Wall -Wextra -Werror -g -fsanitize=address,undefined'
make qsee-supplicant CC=aarch64-linux-gnu-gcc CFLAGS='-std=c11 -Wall -Wextra -Werror -O2' LDFLAGS=-static
install -m 0755 qsee-supplicant "$project/build/kali/fingerprint-listener/aura-qsee-supplicant-test"
sha256sum "$project/build/kali/fingerprint-listener/aura-qsee-supplicant-test"
