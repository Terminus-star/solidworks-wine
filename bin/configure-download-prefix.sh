#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/common.sh"
if [[ "${1:-}" == '--help' ]]; then
    printf 'Usage: configure-download-prefix.sh\nRepair the XMLHTTP alias in the isolated download prefix and verify COM activation.\n'
    exit 0
fi
PREFIX_DIR="$PROJECT_ROOT/download-prefix"
prepare_wine_environment
require_prefix
[[ -f "$PROJECT_ROOT/build/com-probe.exe" ]] || bash "$SCRIPT_DIR/build-helpers.sh"
if ! timeout 25 "$WINE_BIN" "$PROJECT_ROOT/build/com-probe.exe" Msxml2.XMLHTTP; then
    # Winetricks installs native MSXML3 but Wine's version-independent alias
    # still points to the MSXML2 class. Use the installed, tested MSXML3 class.
    timeout 25 "$WINE_BIN" "$PROJECT_ROOT/build/com-probe.exe" Msxml2.XMLHTTP.3.0
    timeout 20 "$WINE_BIN" reg add 'HKCR\Msxml2.XMLHTTP\CLSID' /reg:32 /ve \
        /t REG_SZ /d '{F5078F35-C551-11D3-89B9-0000F81FE221}' /f
fi
timeout 25 "$WINE_BIN" "$PROJECT_ROOT/build/com-probe.exe" \
    Msxml2.XMLHTTP Msxml2.DOMDocument.3.0 Msxml2.DOMDocument.6.0
