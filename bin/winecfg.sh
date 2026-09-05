#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
    printf 'Usage: winecfg.sh\n\nOpen Wine configuration for the dedicated SOLIDWORKS prefix.\n'
    exit 0
fi
[[ $# -eq 0 ]] || die 'This command takes no arguments. Use --help for usage.'

prepare_wine_environment
require_prefix
require_executable "$WINECFG_BIN" winecfg
"$WINECFG_BIN"
wait_for_wineserver
