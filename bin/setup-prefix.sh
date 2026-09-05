#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: setup-prefix.sh [--minimal] [--no-dotnet]

Initialize or update the isolated 64-bit Wine prefix.

  --minimal    Only initialize Wine and set Windows 11 mode.
  --no-dotnet  Install fonts and Visual C++ runtimes, but skip .NET 4.8.

The default installs core fonts, VC++ 2010/2022, MSXML 3/6, and .NET 4.8.
Winetricks downloads redistributables from their upstream vendors.
EOF
}

minimal=0
install_dotnet=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --minimal) minimal=1 ;;
        --no-dotnet) install_dotnet=0 ;;
        --help|-h) usage; exit 0 ;;
        *) die "Unknown option: $1" ;;
    esac
    shift
done

prepare_wine_environment
require_executable "$WINE_BIN" wine
require_executable "$WINEBOOT_BIN" wineboot
require_executable "$WINECFG_BIN" winecfg
require_executable "$WINESERVER_BIN" wineserver

mkdir -p "$PREFIX_DIR" "$LOG_DIR"
exec 9>"$PREFIX_DIR/.solidworks-install.lock"
flock -n 9 || die 'Another controller is using this prefix.'
PYTHONPATH="$PROJECT_ROOT/lib" python3 -c \
    'import os; from pathlib import Path; from solidworks_wine.supervisor import ensure_idle; ensure_idle(Path(os.environ["WINEPREFIX"]))'

if [[ -f "$PREFIX_DIR/system.reg" ]]; then
    note "Updating existing prefix: $PREFIX_DIR"
    timeout --kill-after=10s 180 "$WINEBOOT_BIN" --update
else
    note "Creating a new 64-bit prefix: $PREFIX_DIR"
    timeout --kill-after=10s 180 "$WINEBOOT_BIN" --init
fi
wait_for_wineserver

if (( minimal == 0 )); then
    require_executable "$WINETRICKS_BIN" winetricks
    components=(corefonts vcrun2010 vcrun2022 msxml3 msxml6)
    if (( install_dotnet == 1 )); then
        components+=(dotnet48)
    fi
    note "Installing prerequisites with Winetricks: ${components[*]}"
    timeout --kill-after=10s "${SOLIDWORKS_PREREQUISITE_TIMEOUT:-3600}" "$WINETRICKS_BIN" -q "${components[@]}"
    wait_for_wineserver
fi

# SOLIDWORKS 2026 supports Windows 11; set the reported version after
# Winetricks, since some prerequisite recipes temporarily change it.
note 'Setting the prefix to Windows 11 mode.'
timeout --kill-after=10s 180 "$WINECFG_BIN" -v win11
if (( minimal == 0 )); then
    timeout --kill-after=10s 180 "$WINETRICKS_BIN" -q fontsmooth=rgb
fi
timeout --kill-after=10s 180 "$WINEBOOT_BIN" --update
wait_for_wineserver

note 'Prefix setup complete.'
note 'Next: vendor prerequisites and direct installation in docs/INSTALL.md.'
