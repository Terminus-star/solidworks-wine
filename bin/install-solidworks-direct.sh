#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: install-solidworks-direct.sh [--plan|--verify] [--timeout SECONDS] [--idle-timeout SECONDS]

Install the complete core SOLIDWORKS Design product using serial.txt, with
bounded supervision and a visible MSI progress window. The serial is sent
through stdin to the MSI API helper; generated raw logs are private.
EOF
}

case "${1:-}" in --help|-h) usage; exit 0 ;; esac

prepare_wine_environment
# The native MSXML overrides used by Installation Manager's web requests
# corrupt the core MSI's registration XML and fail its Toolbox XML resource.
# Offline MSI actions complete those operations with Wine's built-in parsers.
case "${SOLIDWORKS_MSI_XML_MODE:-builtin}" in
    builtin) export WINEDLLOVERRIDES="$WINEDLLOVERRIDES;msxml3,msxml6=b" ;;
    prefix) ;;
    *) die 'SOLIDWORKS_MSI_XML_MODE must be builtin or prefix.' ;;
esac
require_prefix
require_executable "$WINE_BIN" wine

command=install
case "${1:-}" in
    --plan) command=plan; shift ;;
    --verify) command=verify; shift ;;
esac
if [[ ! -f "$PROJECT_ROOT/build/msi-tool.exe" || "$PROJECT_ROOT/native/msi-tool.c" -nt "$PROJECT_ROOT/build/msi-tool.exe" ]]; then
    bash "$SCRIPT_DIR/build-helpers.sh"
fi
export SOLIDWORKS_FULL_MEDIA_DIR="$FULL_MEDIA_DIR"
export SOLIDWORKS_SERIAL_FILE="$SERIAL_FILE"
export SOLIDWORKS_LOG_DIR="$LOG_DIR"
if [[ "$command" != install ]]; then
    exec python3 "$SCRIPT_DIR/install-controller.py" "$command" "$@"
fi
python3 "$SCRIPT_DIR/install-controller.py" "$command" "$@"
# The core MSI does not repair the separately packaged managed Login Manager.
# Wait until the core controller has exited and released its prefix lock.
bash "$SCRIPT_DIR/repair-login-manager.sh"
