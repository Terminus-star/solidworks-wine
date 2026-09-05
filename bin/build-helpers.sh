#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/common.sh"
if [[ "${1:-}" == '--help' ]]; then
    printf 'Usage: build-helpers.sh\nBuild the private Windows MSI inspection/install helper.\n'
    exit 0
fi
command -v i686-w64-mingw32-gcc >/dev/null || die 'i686-w64-mingw32-gcc is required.'
mkdir -p "$PROJECT_ROOT/build"
i686-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -municode \
    "$PROJECT_ROOT/native/msi-tool.c" -o "$PROJECT_ROOT/build/msi-tool.exe" -lmsi
note 'Built build/msi-tool.exe'
i686-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -municode \
    "$PROJECT_ROOT/native/window-tool.c" -o "$PROJECT_ROOT/build/window-tool.exe" -luser32
note 'Built build/window-tool.exe'
i686-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -municode \
    "$PROJECT_ROOT/native/com-probe.c" -o "$PROJECT_ROOT/build/com-probe.exe" -lole32 -luuid
note 'Built build/com-probe.exe'
gcc -std=c11 -O2 -Wall -Wextra -Werror \
    "$PROJECT_ROOT/native/media-checksum.c" -o "$PROJECT_ROOT/build/solidworks-checksum"
note 'Built build/solidworks-checksum'
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror \
    "$PROJECT_ROOT/native/header-layout-test.c" -o "$PROJECT_ROOT/build/header-layout-test.exe" -lcomctl32 -luser32
note 'Built build/header-layout-test.exe'
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -municode \
    "$PROJECT_ROOT/native/font-probe.c" -o "$PROJECT_ROOT/build/font-probe.exe" -lgdi32
note 'Built build/font-probe.exe'
