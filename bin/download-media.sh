#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/common.sh"
if [[ "${1:-}" == '--help' ]]; then
    printf '%s\n' 'Usage: download-media.sh' \
        'Run Installation Manager in download-prefix, separate from the application.' \
        'Initialize that prefix with setup-prefix.sh --minimal and winetricks dotnet48 vcrun2022 msxml3 msxml6.' \
        'Control its page with SOLIDWORKS_CDP_URL=http://127.0.0.1:9223 bin/installer-bridge.py.'
    exit 0
fi
application_prefix="$PREFIX_DIR"
PREFIX_DIR="$PROJECT_ROOT/download-prefix"
prepare_wine_environment
require_prefix
exec 9>"$PREFIX_DIR/.solidworks-install.lock"
flock -n 9 || die 'Another controller is using the download prefix.'
PYTHONPATH="$PROJECT_ROOT/lib" python3 -c \
    'import os; from pathlib import Path; from solidworks_wine.supervisor import ensure_idle; ensure_idle(Path(os.environ["WINEPREFIX"]))'
bash "$SCRIPT_DIR/configure-download-prefix.sh"
browser_dir="${SOLIDWORKS_WEBVIEW2_DIR:-}"
if [[ -z "$browser_dir" ]]; then
    browser_prefixes=("$PREFIX_DIR")
    if [[ "$application_prefix" != "$PREFIX_DIR" ]]; then
        browser_prefixes+=("$application_prefix")
    fi
    for browser_prefix in "${browser_prefixes[@]}"; do
        for candidate in "$browser_prefix/drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application/"*; do
            if [[ -f "$candidate/msedgewebview2.exe" ]]; then
                [[ -z "$browser_dir" ]] || die 'Multiple WebView2 runtimes found; choose SOLIDWORKS_WEBVIEW2_DIR explicitly.'
                browser_dir="$candidate"
            fi
        done
        # Prefer the downloader's own runtime; preserve the old application-
        # prefix fallback when it has none, without pinning a machine path.
        [[ -z "$browser_dir" ]] || break
    done
fi
[[ -f "$browser_dir/msedgewebview2.exe" ]] || die 'Set SOLIDWORKS_WEBVIEW2_DIR to the existing WebView2 runtime folder.'
export WEBVIEW2_BROWSER_EXECUTABLE_FOLDER="Z:${browser_dir//\//\\}"
export WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="${WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS//--remote-debugging-port=9222/--remote-debugging-port=9223}"
umask 077
mkdir -p "$LOG_DIR"
log_file="$LOG_DIR/downloader-$(date +%Y%m%d-%H%M%S).log"
note "Downloader log: $log_file"
note 'Downloader automation endpoint: http://127.0.0.1:9223'
trap 'timeout 15 "$WINESERVER_BIN" -k || true' EXIT
timeout --signal=TERM --kill-after=10s "${SOLIDWORKS_DOWNLOAD_TIMEOUT:-1200}" \
    nice -n 10 "$WINE_BIN" "$MEDIA_DIR/sldim/sldIM.exe" 2>&1 | tee "$log_file"
