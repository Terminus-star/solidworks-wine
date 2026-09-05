#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: run-solidworks.sh [--no-splash] [--software-rendering] [--exe PATH] [--] [arguments...]

Launch the installed SLDWORKS.exe from the dedicated prefix.

  --software-rendering  Use Mesa's CPU renderer for graphics troubleshooting.
  --no-splash           Skip the splash for an empty interactive launch (2026 SP3.2).
  --exe PATH            Override automatic SLDWORKS.exe discovery.
EOF
}

software_rendering=0
no_splash=0
solidworks_exe=''
while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-splash) no_splash=1; shift ;;
        --software-rendering) software_rendering=1; shift ;;
        --exe)
            [[ $# -ge 2 ]] || die '--exe requires a path.'
            solidworks_exe="$2"
            shift 2
            ;;
        --help|-h) usage; exit 0 ;;
        --) shift; break ;;
        -*) die "Unknown option: $1" ;;
        *) break ;;
    esac
done

prepare_wine_environment
require_prefix
require_executable "$WINE_BIN" wine

if [[ -z "$solidworks_exe" ]]; then
    search_roots=(
        "$PREFIX_DIR/drive_c/Program Files/SOLIDWORKS Corp"
        "$PREFIX_DIR/drive_c/Program Files"
    )
    for search_root in "${search_roots[@]}"; do
        [[ -d "$search_root" ]] || continue
        solidworks_exe="$(find "$search_root" -type f -iname 'SLDWORKS.exe' -print -quit 2>/dev/null || true)"
        [[ -n "$solidworks_exe" ]] && break
    done
fi

[[ -n "$solidworks_exe" && -f "$solidworks_exe" ]] || die 'SLDWORKS.exe was not found. Complete installation first or pass --exe PATH.'

mkdir -p "$LOG_DIR"
log_file="$LOG_DIR/solidworks-$(date +%Y%m%d-%H%M%S).log"
if (( software_rendering == 1 )); then
    export LIBGL_ALWAYS_SOFTWARE=1
    warn 'Software rendering is enabled; expect substantially lower graphics performance.'
fi

note "Launching $solidworks_exe"
note "Console output will be saved to $log_file"
startup_args=()
if (( no_splash == 1 )); then
    # This version suppresses the splash with /m even without a macro file.
    # Only use it on an otherwise empty command line: with document/macro
    # arguments, /m can change their meaning. Keep normal forwarding there.
    # This is a tested compatibility behavior, not a documented /nosplash flag.
    if (( $# == 0 )); then
        startup_args=(/m)
        note 'Skipping the startup splash; normal initialization still takes time.'
    else
        warn 'Keeping normal startup mode for the supplied document/macro arguments.'
    fi
fi
WINEDEBUG="${WINEDEBUG:--all}" "$WINE_BIN" "$solidworks_exe" "$@" "${startup_args[@]}" 2>&1 | tee "$log_file"
