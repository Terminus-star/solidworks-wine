#!/usr/bin/env bash
# sw-overlay.sh — optional: a writable overlay over a read-only Windows
# partition, so SOLIDWORKS under Wine can write files without changing
# Windows. Useful for a first trial; for daily use mount read-write instead.
#
# Usage (needs root for mount):
#   sudo inplace/sw-overlay.sh up       make /mnt/windows read-only, mount overlay
#   sudo inplace/sw-overlay.sh down     unmount overlay (Windows stays read-only)
#        inplace/sw-overlay.sh status   show mounts and how much was written
# Then link through it:  WIN_ROOT=<overlay>/merged inplace/sw-link.sh
#
# Environment overrides:
#   LOWER        the Windows mount (default /mnt/windows)
#   OVERLAY_DIR  where upper/work/merged live
#                (default ~/.local/share/solidworks-wine/win-overlay)
#
# Layout (overlayfs):
#   lower  = /mnt/windows             read-only; the real Windows files
#   upper  = $OVERLAY_DIR/upper       every created/changed file lands here
#   work   = $OVERLAY_DIR/work        kernel scratch space (must be empty)
#   merged = $OVERLAY_DIR/merged      combined view the Wine prefix uses
#
# Reading a file reads it from lower. Writing one first copies it up into
# upper ("copy-up") and changes the copy, so lower never changes. To throw
# everything away: down, then delete upper/ and work/.
#
# Lower must stay read-only while the overlay is mounted (changing it
# underneath overlayfs is undefined), and never boot Windows (VM or native)
# while /mnt/windows is mounted here at all. While the overlay is up it keeps
# /mnt/windows busy, so run `down` before unmounting.

set -euo pipefail

LOWER="${LOWER:-/mnt/windows}"
# Under sudo, $HOME may be root's; use the invoking user's home instead.
USER_HOME=$(getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6)
BASE="${OVERLAY_DIR:-$USER_HOME/.local/share/solidworks-wine/win-overlay}"
UPPER="$BASE/upper"
WORK="$BASE/work"
MERGED="$BASE/merged"
# Owner for the dirs we create: the user who ran sudo, not root.
OWNER="${SUDO_UID:-$(id -u)}:${SUDO_GID:-$(id -g)}"

need_root() {
    [[ $EUID -eq 0 ]] || { echo "sw-overlay: run with sudo" >&2; exit 1; }
}

case "${1:-status}" in
up)
    need_root
    # -f matches the full command line; -x on the name can't work because
    # Linux truncates process names to 15 characters ("qemu-system-x86").
    if pgrep -f '^qemu-system-x86_64 ' >/dev/null; then
        echo "sw-overlay: a QEMU VM is running; refusing" >&2
        exit 1
    fi
    mountpoint -q "$LOWER" || { echo "sw-overlay: $LOWER is not mounted" >&2; exit 1; }
    if mountpoint -q "$MERGED"; then
        echo "sw-overlay: already mounted at $MERGED"
        exit 0
    fi

    # Make the mount *point* read-only (bind flag), not the filesystem: with a
    # read-only superblock some NTFS drivers report files as r-x, and overlayfs
    # copies those modes up, so nothing in the overlay would be writable.
    mount -o remount,bind,ro "$LOWER"
    mkdir -p "$UPPER" "$WORK" "$MERGED"
    chown "$OWNER" "$BASE" "$UPPER" "$MERGED"
    mount -t overlay overlay \
        -o "lowerdir=$LOWER,upperdir=$UPPER,workdir=$WORK" "$MERGED"
    echo "sw-overlay: up — $LOWER read-only, writes go to $UPPER"
    ;;
down)
    need_root
    if mountpoint -q "$MERGED"; then
        umount "$MERGED"
    fi
    echo "sw-overlay: down — $LOWER is still read-only; changes kept in $UPPER"
    echo "            (make it writable again: sudo mount -o remount,bind,rw $LOWER)"
    ;;
status)
    findmnt -o TARGET,VFS-OPTIONS,FS-OPTIONS "$LOWER" || echo "$LOWER not mounted"
    findmnt -o TARGET,FSTYPE,OPTIONS "$MERGED" || echo "overlay not mounted"
    if [[ -d "$UPPER" ]]; then
        echo "written so far: $(du -sh "$UPPER" 2>/dev/null | cut -f1) in $UPPER"
    fi
    ;;
*)
    echo "usage: $0 up|down|status" >&2
    exit 1
    ;;
esac
