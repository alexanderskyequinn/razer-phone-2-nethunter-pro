#!/bin/bash
set -euo pipefail
tools_dir=$(cd "$(dirname "$0")" && pwd)
unshare --mount --propagation private bash "$tools_dir/build_kali_resumable.sh"
unshare --mount --propagation private bash "$tools_dir/install_kali_desktop.sh"
