#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: diagnose.sh [--stdout]

Collect host, graphics, prefix, and prerequisite diagnostics. The report does
not dump the registry or include the SOLIDWORKS serial number.
EOF
}

stdout_only=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --stdout) stdout_only=1 ;;
        --help|-h) usage; exit 0 ;;
        *) die "Unknown option: $1" ;;
    esac
    shift
done

prepare_wine_environment
mkdir -p "$LOG_DIR"
report="$LOG_DIR/diagnostics-$(date +%Y%m%d-%H%M%S).txt"

collect() {
    printf 'SOLIDWORKS Wine diagnostics\n'
    printf 'Generated: %s\n' "$(date --iso-8601=seconds)"
    printf 'Project: %s\n' "$PROJECT_ROOT"
    printf 'Prefix: %s\n' "$PREFIX_DIR"
    printf 'Installer: %s\n' "$INSTALLER"
    printf '\n[host]\n'
    uname -a
    if [[ -f /etc/os-release ]]; then
        rg '^(PRETTY_NAME|VERSION_CODENAME)=' /etc/os-release || true
    fi
    free -h || true
    df -h "$PROJECT_ROOT" || true
    lspci 2>/dev/null | rg -i 'VGA compatible|3D controller|Display controller' || true

    printf '\n[tools]\n'
    timeout 15 "$WINE_BIN" --version 2>&1 || true
    "$WINETRICKS_BIN" --version 2>&1 | head -n 2 || true
    7z i 2>/dev/null | head -n 2 || true

    printf '\n[graphics]\n'
    if command -v glxinfo >/dev/null 2>&1 && [[ -n "${DISPLAY:-}" ]]; then
        glxinfo -B 2>&1 || true
    else
        printf 'glxinfo unavailable or no DISPLAY set.\n'
    fi

    printf '\n[installer]\n'
    if [[ -f "$INSTALLER" ]]; then
        stat -c 'size=%s bytes modified=%y' "$INSTALLER"
        sha256sum "$INSTALLER"
        if [[ -f "$MEDIA_DIR/sldim/sldim.xml" ]]; then
            rg -m 1 '<(SuiteName|Version|BuildVersion)>' "$MEDIA_DIR/sldim/sldim.xml" || true
        fi
    else
        printf 'Installer missing.\n'
    fi

    printf '\n[prefix]\n'
    if [[ -f "$PREFIX_DIR/system.reg" ]]; then
        du -sh "$PREFIX_DIR" 2>/dev/null || true
        timeout 20 "$WINE_BIN" cmd /c ver 2>&1 || true
        timeout 20 "$WINE_BIN" reg query 'HKLM\Software\Microsoft\NET Framework Setup\NDP\v4\Full' /v Release 2>&1 || true
        find "$PREFIX_DIR/drive_c/Program Files" -type f -iname 'SLDWORKS.exe' -print 2>/dev/null || true
    else
        printf 'Prefix is not initialized.\n'
    fi

    printf '\n[recent logs]\n'
    find "$LOG_DIR" -maxdepth 1 -type f -printf '%TY-%Tm-%Td %TH:%TM %f (%s bytes)\n' 2>/dev/null | sort | tail -n 20 || true
}

if (( stdout_only == 1 )); then
    collect
else
    collect | tee "$report"
    note "Diagnostic report saved to $report"
fi
