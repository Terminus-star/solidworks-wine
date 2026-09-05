#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: install-solidworks.sh [--extract-only] [--refresh-media] [--debug]

Extract the supplied SOLIDWORKS bootstrapper into this project and launch its
setup.exe inside the dedicated Wine prefix.

  --extract-only   Prepare media but do not launch the graphical installer.
  --refresh-media  Re-extract media even when setup.exe already exists.
  --debug          Record Wine exception diagnostics for an early crash.

The serial number is intentionally not accepted on the command line or stored
in this folder. Enter it in the graphical Installation Manager when prompted.
EOF
}

extract_only=0
refresh_media=0
debug_mode=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --extract-only) extract_only=1 ;;
        --refresh-media) refresh_media=1 ;;
        --debug) debug_mode=1 ;;
        --help|-h) usage; exit 0 ;;
        *) die "Unknown option: $1" ;;
    esac
    shift
done

prepare_wine_environment
require_prefix
require_executable "$WINE_BIN" wine
command -v 7z >/dev/null 2>&1 || die '7z is required (Linux Mint package: p7zip-full).'
[[ -f "$INSTALLER" ]] || die "Installer not found: $INSTALLER"

setup_exe="$MEDIA_DIR/setup.exe"
if (( refresh_media == 1 )) || [[ ! -f "$setup_exe" ]]; then
    mkdir -p "$MEDIA_DIR"
    note "Extracting $(basename -- "$INSTALLER") into $MEDIA_DIR"
    7z x -y "-o$MEDIA_DIR" "$INSTALLER"
fi

# p7zip 16 on Ubuntu 22.04 preserves backslashes in a handful of ZIP member
# names as literal Linux filename characters. Convert those members to the
# directory layout expected by setup.exe.
while IFS= read -r -d '' source_path; do
    relative_path="${source_path#"$MEDIA_DIR/"}"
    normalized_path="${relative_path//\\//}"
    target_path="$MEDIA_DIR/$normalized_path"
    mkdir -p "$(dirname -- "$target_path")"
    mv -f -- "$source_path" "$target_path"
done < <(find "$MEDIA_DIR" -type f -name '*\\*' -print0)

[[ -f "$setup_exe" ]] || die "Extraction did not produce $setup_exe"

if [[ -f "$MEDIA_DIR/sldim/sldim.xml" ]]; then
    suite="$(rg -o -m 1 '<SuiteName>[^<]+' "$MEDIA_DIR/sldim/sldim.xml" | sed 's/<SuiteName>//' || true)"
    [[ -n "$suite" ]] && note "Prepared installer: $suite"
fi

if (( extract_only == 1 )); then
    note 'Media extraction complete; the installer was not launched.'
    exit 0
fi

prepare_spatial_iop_payload

mkdir -p "$LOG_DIR"
log_file="$LOG_DIR/installer-$(date +%Y%m%d-%H%M%S).log"
note 'Launching SOLIDWORKS Installation Manager.'
note 'Enter your licensed serial number in the installer UI when prompted.'
note "Console output will be saved to $log_file"

wine_debug="${WINEDEBUG:--all}"
if (( debug_mode == 1 )); then
    wine_debug='+timestamp,+pid,+seh'
    note 'Wine exception tracing is enabled for this launch.'
fi

pushd "$MEDIA_DIR" >/dev/null
set +e
WINEDEBUG="$wine_debug" "$WINE_BIN" "$setup_exe" 2>&1 | tee "$log_file"
installer_status=${PIPESTATUS[0]}
set -e
popd >/dev/null
wait_for_wineserver

if (( installer_status != 0 )); then
    die "Installation Manager exited with status $installer_status. Run $PROJECT_ROOT/bin/diagnose.sh and inspect $log_file"
fi

note 'Installation Manager closed successfully.'
note "After installation, start SOLIDWORKS with $PROJECT_ROOT/bin/run-solidworks.sh"
