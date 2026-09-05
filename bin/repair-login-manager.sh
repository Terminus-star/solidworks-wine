#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/common.sh"
if [[ "${1:-}" == '--help' ]]; then
    printf 'Usage: repair-login-manager.sh\nRepair the bundled SOLIDWORKS Login Manager prerequisite.\n'
    exit 0
fi
prepare_wine_environment
require_prefix
export WINEDLLOVERRIDES="$WINEDLLOVERRIDES;msxml3,msxml6=b"
export SOLIDWORKS_FULL_MEDIA_DIR="$FULL_MEDIA_DIR" SOLIDWORKS_SERIAL_FILE="$SERIAL_FILE"
exec python3 "$SCRIPT_DIR/repair-login-manager.py"
