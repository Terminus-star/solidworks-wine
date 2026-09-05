#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/common.sh"
case "${1:-}" in --help|-h)
    printf '%s\n' 'Usage: install-vendor-prerequisites.sh --plan|--install' \
        'Install VBA 7.1, VSTA 2022, and CEF from your own complete vendor media.' \
        'Review the vendor terms, close SOLIDWORKS, and read docs/INSTALL.md first.'
    exit 0 ;;
esac
prepare_wine_environment
export SOLIDWORKS_FULL_MEDIA_DIR="$FULL_MEDIA_DIR" SOLIDWORKS_LOG_DIR="$LOG_DIR"
exec python3 "$SCRIPT_DIR/install-vendor-prerequisites.py" "$@"
