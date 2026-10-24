#!/usr/bin/env bash
# install-shortcut.sh — install the launcher, an app-menu entry and its icon
# for the current user.
#
# Usage:
#   inplace/install-shortcut.sh
#
# Environment overrides:
#   WIN_ROOT   mounted Windows partition (default /mnt/windows), used to read
#              the icon out of SLDWORKS.exe
#
# Installs:
#   ~/.local/bin/solidworks-2022
#   ~/.local/share/applications/solidworks-2022.desktop
#   ~/.local/share/icons/hicolor/<size>/apps/solidworks-2022.png
# The icon is extracted from your own SLDWORKS.exe (wrestool/icotool from
# icoutils); SOLIDWORKS artwork is never stored in this repository.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WIN_ROOT="${WIN_ROOT:-/mnt/windows}"
BIN="$HOME/.local/bin/solidworks-2022"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT

# 1. Launcher
install -Dm755 "$HERE/solidworks-2022" "$BIN"
echo "launcher: $BIN"

# 2. Icon: take the largest icon group from SLDWORKS.exe and install every
#    full-colour (32-bit) size it contains.
exe=$(find "$WIN_ROOT/Program Files/SOLIDWORKS Corp" "$WIN_ROOT/Program Setups/SolidWorks" \
          -maxdepth 2 -iname 'SLDWORKS.exe' -print -quit 2>/dev/null || true)
if [[ -n "$exe" ]] && command -v wrestool >/dev/null && command -v icotool >/dev/null; then
    group=$(wrestool -l --type=group_icon "$exe" \
        | sed -nE 's/.*--name=([^ ]+) .*size=([0-9]+)\].*/\2 \1/p' | sort -rn | head -n 1 | cut -d' ' -f2)
    wrestool -x --type=group_icon --name="$group" -o "$TMP/sw.ico" "$exe"
    icotool -l "$TMP/sw.ico" \
      | sed -nE 's/.*--index=([0-9]+) --width=([0-9]+) .*--bit-depth=32.*/\1 \2/p' \
      | while read -r idx size; do
            icotool -x --index="$idx" -o "$TMP/$size.png" "$TMP/sw.ico"
            install -Dm644 "$TMP/$size.png" "$ICONS/${size}x${size}/apps/solidworks-2022.png"
        done
    echo "icon: installed from $exe"
else
    echo "icon: skipped (SLDWORKS.exe not found under $WIN_ROOT, or icoutils missing)"
fi

# 3. Menu entry, with the launcher's absolute path (desktop sessions don't
#    always have ~/.local/bin on PATH). A non-default WINE_BIN (e.g. the
#    stock /opt/wine-cachyos) is recorded in the entry so the menu uses it.
exec_line="$BIN"
if [[ -n "${WINE_BIN:-}" && "$WINE_BIN" != /opt/wine-cachyos-portal/bin/wine ]]; then
    exec_line="env WINE_BIN=$WINE_BIN $BIN"
fi
mkdir -p "$APPS"
sed "s|@LAUNCHER@|$exec_line|" "$HERE/solidworks-2022.desktop.in" > "$APPS/solidworks-2022.desktop"
desktop-file-validate "$APPS/solidworks-2022.desktop"
echo "menu entry: $APPS/solidworks-2022.desktop"

# 4. Register with app menus / launchers.
update-desktop-database "$APPS" 2>/dev/null || true
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true
echo "registered — look for \"SOLIDWORKS\" in your app menu"
