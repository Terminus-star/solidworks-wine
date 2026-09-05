#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/common.sh"
case "${1:-}" in
    --help|-h)
        printf 'Usage: install-desktop-shortcut.sh [--desktop-dir PATH] [--replace]\nGenerate a shortcut for this clone and configured prefix/runtime.\nExisting different shortcuts require --replace and are backed up.\n'
        exit 0 ;;
esac
export WINEPREFIX="$PREFIX_DIR" WINE_BIN
exec python3 "$SCRIPT_DIR/install-desktop-shortcut.py" "$@"
