#!/usr/bin/env bash
# sw-link.sh — make the existing Windows SOLIDWORKS install appear inside the
# Wine prefix at the same C:\ paths the registry export refers to, and add a
# W: drive for the Windows partition.
#
# Usage:
#   inplace/sw-link.sh
#   WIN_ROOT=~/.local/share/solidworks-wine/win-overlay/merged inplace/sw-link.sh
#                                      (link through the overlay, see sw-overlay.sh)
#
# Environment overrides:
#   WIN_ROOT   where the Windows C:\ drive is visible (default /mnt/windows)
#   PREFIX     the Wine prefix (default ~/.local/share/wineprefixes/solidworks-2022)
#
# Each entry becomes a symlink, e.g.
#   prefix/drive_c/Program Files/SOLIDWORKS Corp -> $WIN_ROOT/Program Files/SOLIDWORKS Corp
# Re-running replaces our own symlinks, so switching WIN_ROOT is one re-run.
# A real directory already at a link path is never touched; the script stops.
#
# If SOLIDWORKS is installed somewhere non-default, add its folder (relative
# to C:\) to LINKS below — it must match the paths stored in the registry.

set -euo pipefail

WIN_ROOT="${WIN_ROOT:-/mnt/windows}"
PREFIX="${PREFIX:-$HOME/.local/share/wineprefixes/solidworks-2022}"
DRIVE_C="$PREFIX/drive_c"

# Paths relative to C:\ — common install locations, the 64- and 32-bit shared
# components, and per-machine data (SOLIDWORKS CAM keeps its material library
# there). Entries missing on the Windows side are skipped.
LINKS=(
    "Program Files/SOLIDWORKS Corp"
    "Program Setups/SolidWorks"
    "Program Files/Common Files/SOLIDWORKS Shared"
    "Program Files (x86)/Common Files/SOLIDWORKS Shared"
    "ProgramData/SOLIDWORKS"
)

[[ -d "$DRIVE_C" ]]  || { echo "sw-link: no prefix at $PREFIX" >&2; exit 1; }
[[ -d "$WIN_ROOT" ]] || { echo "sw-link: $WIN_ROOT not found (mounted?)" >&2; exit 1; }

for rel in "${LINKS[@]}"; do
    target="$WIN_ROOT/$rel"
    link="$DRIVE_C/$rel"
    if [[ ! -e "$target" ]]; then
        echo "  skip (not on the Windows side): $rel"
        continue
    fi
    if [[ -e "$link" && ! -L "$link" ]]; then
        echo "sw-link: $link is a real directory, not our symlink; stopping" >&2
        exit 1
    fi
    mkdir -p "$(dirname "$link")"
    # -n: if $link is already a symlink to a directory, replace the link
    # itself instead of creating a new link inside that directory.
    ln -sfn "$target" "$link"
    echo "  $rel -> $target"
done

# W: = the whole Windows partition, so files there open as W:\Users\...
# (Z:\ also reaches them, but Z:\mnt\windows\... is longer.)
ln -sfn "$WIN_ROOT" "$PREFIX/dosdevices/w:"
echo "  W: -> $WIN_ROOT"
