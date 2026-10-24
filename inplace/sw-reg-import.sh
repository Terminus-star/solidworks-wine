#!/usr/bin/env bash
# sw-reg-import.sh — import the files written by sw-reg-export.sh into the
# Wine prefix, then spot-check that strings arrived intact.
#
# Usage:
#   inplace/sw-reg-import.sh
#
# Environment overrides:
#   WINE_BIN   default /opt/wine-cachyos-portal/bin/wine
#   PREFIX     default ~/.local/share/wineprefixes/solidworks-2022
#   IN         directory written by sw-reg-export.sh (default ./sw-registry)
#
# Re-running is safe: importing overwrites the same keys with the same values.
# `regedit /S` reports nothing even when it mangles data, hence the check.

set -euo pipefail

WINE_BIN="${WINE_BIN:-/opt/wine-cachyos-portal/bin/wine}"
PREFIX="${PREFIX:-$HOME/.local/share/wineprefixes/solidworks-2022}"
IN="${IN:-$PWD/sw-registry}"

[[ -x "$WINE_BIN" ]] || { echo "sw-reg-import: $WINE_BIN not found" >&2; exit 1; }
[[ -d "$PREFIX/drive_c" ]] || { echo "sw-reg-import: no prefix at $PREFIX" >&2; exit 1; }
[[ -d "$IN/import" ]] || { echo "sw-reg-import: run inplace/sw-reg-export.sh first ($IN/import missing)" >&2; exit 1; }

wine() { WINEPREFIX="$PREFIX" WINEDEBUG=-all "$WINE_BIN" "$@" 2>/dev/null; }

for f in hklm-vendor.reg hkcu-vendor.reg hklm-com.reg; do
    # regedit needs a Windows path; winepath converts /home/... to Z:\home\...
    win_path=$(wine winepath -w "$IN/import/$f" | tr -d '\r')
    echo "importing $f"
    wine regedit /S "$win_path"
done

# A file association must come back as the full ProgID, not one character.
value=$(wine reg query 'HKLM\Software\Classes\.sldprt' /ve | tr -d '\r' | awk '/REG_SZ/ {print $NF}')
if [[ "$value" == SldPart.Document* ]]; then
    echo "check ok: .sldprt -> $value"
else
    echo "check FAILED: .sldprt -> '$value' (expected SldPart.Document...)" >&2
    exit 1
fi
