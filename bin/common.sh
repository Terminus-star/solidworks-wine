#!/usr/bin/env bash
# Public variables below are consumed by sourcing entrypoints.
# shellcheck disable=SC2034

# Shared paths and helpers for the SOLIDWORKS Wine launchers.

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
PREFIX_DIR="${WINEPREFIX:-$PROJECT_ROOT/prefix}"
INSTALLER="${SOLIDWORKS_INSTALLER:-$HOME/Downloads/SolidWorksSetup.exe}"
MEDIA_DIR="${SOLIDWORKS_MEDIA_DIR:-$PROJECT_ROOT/media}"
FULL_MEDIA_DIR="${SOLIDWORKS_FULL_MEDIA_DIR:-$PROJECT_ROOT/full-media}"
SERIAL_FILE="${SOLIDWORKS_SERIAL_FILE:-$PROJECT_ROOT/serial.txt}"
LOG_DIR="${SOLIDWORKS_LOG_DIR:-$PROJECT_ROOT/logs}"

resolve_command() {
    local requested="$1"
    local fallback="$2"

    if [[ -n "$requested" ]]; then
        printf '%s\n' "$requested"
    elif command -v "$fallback" >/dev/null 2>&1; then
        command -v "$fallback"
    else
        printf '%s\n' "$fallback"
    fi
}

companion_command() {
    local base="$1"
    local name="$2"
    local candidate
    candidate="$(dirname -- "$base")/$name"

    if [[ -x "$candidate" ]]; then
        printf '%s\n' "$candidate"
    elif command -v "$name" >/dev/null 2>&1; then
        command -v "$name"
    else
        printf '%s\n' "$candidate"
    fi
}

LOCAL_WINE_BIN="$PROJECT_ROOT/wine-runtime/bin/wine"
requested_wine="${WINE_BIN:-}"
if [[ -z "$requested_wine" && -x "$LOCAL_WINE_BIN" ]]; then
    requested_wine="$LOCAL_WINE_BIN"
fi

WINE_BIN="$(resolve_command "$requested_wine" wine)"
WINE64_BIN="$(companion_command "$WINE_BIN" wine64)"
# New-WoW64 builds (one `wine` for 32- and 64-bit, e.g. Wine 10+ distro
# packages) ship no wine64; companion_command then returns a missing path,
# which winetricks would trust. Fall back to wine itself, as winetricks does.
[[ -x "$WINE64_BIN" ]] || WINE64_BIN="$WINE_BIN"
WINEBOOT_BIN="$(companion_command "$WINE_BIN" wineboot)"
WINESERVER_BIN="$(companion_command "$WINE_BIN" wineserver)"
WINECFG_BIN="$(companion_command "$WINE_BIN" winecfg)"
WINETRICKS_BIN="$(resolve_command "${WINETRICKS_BIN:-}" winetricks)"

note() {
    printf '[solidworks-wine] %s\n' "$*"
}

warn() {
    printf '[solidworks-wine] WARNING: %s\n' "$*" >&2
}

die() {
    printf '[solidworks-wine] ERROR: %s\n' "$*" >&2
    exit 1
}

require_executable() {
    local executable="$1"
    local label="${2:-$1}"
    [[ -x "$executable" ]] || die "$label was not found or is not executable: $executable"
}

prepare_wine_environment() {
    export WINEPREFIX="$PREFIX_DIR"
    export WINEARCH=win64
    export WINE="$WINE_BIN"
    export WINE64="$WINE64_BIN"
    export WINESERVER="$WINESERVER_BIN"
    export WINEDEBUG="${WINEDEBUG:--all}"

    # The Installation Manager uses native MSXML with an asynchronous URLMon
    # stream, then expects the XML callback to have completed before load()
    # returns. Enable the matching opt-in behavior in our private URLMon build.
    export SOLIDWORKS_URLMON_SYNC_BINDTOSTORAGE="${SOLIDWORKS_URLMON_SYNC_BINDTOSTORAGE:-1}"

    # The Login Manager and main SOLIDWORKS MSI packages complete their
    # RegTlb/RegSvr/RegAsm/NGen work, then their registration custom actions
    # can terminate with an access violation (or, when winedbg is active,
    # STATUS_DEBUGGER_INACTIVE) under Wine. The project-private MSI build
    # treats only those exact product/action/status combinations as nonfatal
    # and replaces the dead custom-action server.
    export SOLIDWORKS_MSI_IGNORE_REGISTRATION_DEBUGGER_INACTIVE="${SOLIDWORKS_MSI_IGNORE_REGISTRATION_DEBUGGER_INACTIVE:-1}"

    # WebView2's DirectComposition/GPU presentation path does not paint its
    # child surface under Wine, leaving the Installation Manager body black.
    # Force Chromium's software compositor and SwiftShader renderer. Disable
    # MojoIpcz as well: under Wine it can spin the wineserver after the manager
    # replaces the welcome page with the serial-number page. These flags affect
    # only WebView2 processes launched here.
    export WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="${WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS:---disable-gpu --disable-gpu-compositing --disable-direct-composition --use-gl=angle --use-angle=swiftshader --disable-gpu-sandbox --no-sandbox --disable-features=MojoIpcz,RendererCodeIntegrity --edge-webview-disable-mojo-ipcz --remote-debugging-port=9222}"

    # Keep Wine from creating host-wide file associations and menu entries for
    # applications in this dedicated prefix. Also prevent unattended installer
    # exceptions from blocking forever in Wine's interactive debugger.
    if [[ -z "${WINEDLLOVERRIDES:-}" ]]; then
        export WINEDLLOVERRIDES='winemenubuilder.exe=d;winedbg.exe=d'
    elif [[ "$WINEDLLOVERRIDES" != *'winemenubuilder.exe='* ]]; then
        export WINEDLLOVERRIDES="$WINEDLLOVERRIDES;winemenubuilder.exe=d"
    fi
    if [[ "$WINEDLLOVERRIDES" != *'winedbg.exe='* ]]; then
        export WINEDLLOVERRIDES="$WINEDLLOVERRIDES;winedbg.exe=d"
    fi

    # The Codex/Nix launch environment can inject newer GL libraries and DRI
    # drivers that are incompatible with Linux Mint 21's system GLVND/Mesa.
    # Normal terminals usually do not have these overrides.
    local graphics_override
    local removed_override=0
    for graphics_override in LD_LIBRARY_PATH LIBGL_DRIVERS_PATH GBM_BACKENDS_PATH; do
        if [[ "${!graphics_override:-}" == *'/nix/store/'* ]]; then
            unset "$graphics_override"
            removed_override=1
        fi
    done
    if (( removed_override == 1 )); then
        warn 'Ignoring Nix-injected graphics paths so Wine uses the host graphics stack.'
    fi
}

require_prefix() {
    [[ -f "$PREFIX_DIR/system.reg" ]] || die "Wine prefix is not initialized. Run $PROJECT_ROOT/bin/setup-prefix.sh first."
}

prepare_spatial_iop_payload() {
    local archive target first_file last_file
    local archive_candidate

    archive=''
    if [[ -f "$FULL_MEDIA_DIR/swwi/data/spatialiop.zip" ]]; then
        archive="$FULL_MEDIA_DIR/swwi/data/spatialiop.zip"
    fi
    for archive_candidate in \
        "$PREFIX_DIR"/drive_c/users/*/Downloads/"SOLIDWORKS Downloads"/*/swwi/data/spatialiop.zip; do
        [[ -n "$archive" ]] && break
        if [[ -f "$archive_candidate" ]]; then
            archive="$archive_candidate"
            break
        fi
    done
    [[ -n "$archive" ]] || return 0

    target="$PREFIX_DIR/drive_c/Program Files/SOLIDWORKS Corp/SOLIDWORKS/spiop/files"
    first_file="$target/code/bin/7z.dll"
    last_file="$target/startup/XCAD/EntityMapping/REVIT_BimTypeToNeutralID.xml"

    if [[ ! -f "$first_file" || ! -f "$last_file" ]]; then
        command -v 7z >/dev/null 2>&1 || die '7z is required to prepare the Spatial IOP payload.'
        note 'Pre-extracting the Spatial IOP payload for Wine shell compatibility.'
        mkdir -p "$target"
        7z x -y "-o$target" "$archive" || die 'Could not extract the Spatial IOP payload.'
    fi

    [[ -f "$first_file" && -f "$last_file" ]] || die 'The Spatial IOP payload is incomplete.'
    export SOLIDWORKS_MSI_SPATIAL_IOP_PREEXTRACTED=1
}

stage_scheduler_resources() {
    local cabinet source_dir target_dir

    cabinet="$FULL_MEDIA_DIR/swwi/data/i386_B~1.cab"
    [[ -f "$cabinet" ]] || die "Task Scheduler resource cabinet not found: $cabinet"
    command -v 7z >/dev/null 2>&1 || die '7z is required to stage Task Scheduler resources.'

    source_dir="$(mktemp -d)"
    target_dir="$PREFIX_DIR/drive_c/Program Files/SOLIDWORKS Corp/SOLIDWORKS/swScheduler/lang/english"
    7z e -y "-o$source_dir" "$cabinet" swboengineresu.dll3 swbackofficeresu.dll3 >/dev/null
    mkdir -p "$target_dir"
    install -m 0644 "$source_dir/swboengineresu.dll3" "$target_dir/swBoEngineResu.dll"
    install -m 0644 "$source_dir/swbackofficeresu.dll3" "$target_dir/swBackOfficeResu.dll"
    rm -rf -- "$source_dir"
    note 'Staged Task Scheduler language resources required before its registration action.'
}

wait_for_wineserver() {
    require_executable "$WINESERVER_BIN" wineserver
    timeout --signal=TERM --kill-after=5s "${SOLIDWORKS_WINE_WAIT_TIMEOUT:-180}" "$WINESERVER_BIN" -w \
        || die 'Wine did not become idle in time. Processes were left intact; inspect this prefix before retrying.'
}
