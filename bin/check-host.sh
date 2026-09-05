#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

usage() {
    cat <<'EOF'
Usage: check-host.sh

Run non-destructive checks for the dedicated SOLIDWORKS Wine environment.
Override paths with WINE_BIN, WINEPREFIX, or SOLIDWORKS_INSTALLER.
EOF
}

if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
    usage
    exit 0
fi
[[ $# -eq 0 ]] || die 'This command takes no arguments. Use --help for usage.'

prepare_wine_environment

errors=0
warnings=0

pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; errors=$((errors + 1)); }
advisory() { printf 'WARN  %s\n' "$*"; warnings=$((warnings + 1)); }

printf 'SOLIDWORKS-on-Wine host check\n'
printf 'Project:   %s\n' "$PROJECT_ROOT"
printf 'Prefix:    %s\n' "$PREFIX_DIR"
printf 'Installer: %s\n\n' "$INSTALLER"

if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    printf 'Host OS:   %s\n' "${PRETTY_NAME:-unknown}"
fi

if [[ -f "$INSTALLER" ]]; then
    installer_size="$(stat -c '%s' "$INSTALLER")"
    if (( installer_size >= 100000000 )); then
        pass "Installer found ($(numfmt --to=iec-i --suffix=B "$installer_size" 2>/dev/null || printf '%s bytes' "$installer_size"))."
    else
        advisory "Installer is unexpectedly small ($installer_size bytes)."
    fi
elif [[ -f "$FULL_MEDIA_DIR/swwi/data/solidworks.msi" ]]; then
    pass 'Complete-media route selected; bootstrapper is not required (MSI payload audit follows separately).'
else
    fail "Neither bootstrapper nor core MSI found; configure SOLIDWORKS_INSTALLER or SOLIDWORKS_FULL_MEDIA_DIR."
fi

if [[ -x "$WINE_BIN" ]]; then
    if wine_version="$(timeout 15 "$WINE_BIN" --version 2>&1)"; then
        pass "Wine available: $wine_version ($WINE_BIN)"
    else
        fail "Wine did not run successfully: ${wine_version:-no output}"
    fi
else
    fail "Wine executable not found: $WINE_BIN"
fi

for dependency in "$WINEBOOT_BIN" "$WINESERVER_BIN" "$WINECFG_BIN" "$WINETRICKS_BIN"; do
    if [[ -x "$dependency" ]]; then
        pass "Found $dependency"
    else
        fail "Missing executable: $dependency"
    fi
done

if command -v 7z >/dev/null 2>&1; then
    pass '7z is available for deterministic installer extraction.'
else
    fail '7z is missing (install package p7zip-full).'
fi

if command -v dpkg >/dev/null 2>&1; then
    if dpkg --print-foreign-architectures | rg -qx 'i386'; then
        pass 'i386 multiarch is enabled.'
    else
        advisory 'i386 multiarch is not enabled; 32-bit installer helpers can fail.'
    fi

    for package in libgl1-mesa-dri:i386 libvulkan1:i386 mesa-vulkan-drivers:i386; do
        if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | rg -q 'ok installed'; then
            pass "$package is installed."
        else
            advisory "$package is not installed."
        fi
    done
fi

available_kib="$(df -Pk "$PROJECT_ROOT" | awk 'NR == 2 {print $4}')"
if (( available_kib >= 35 * 1024 * 1024 )); then
    pass "At least 35 GiB is free ($(numfmt --from-unit=1024 --to=iec-i --suffix=B "$available_kib" 2>/dev/null || printf '%s KiB' "$available_kib"))."
else
    advisory "Less than 35 GiB is free; a full SOLIDWORKS download/install may run out of space."
fi

memory_kib="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
if (( memory_kib >= 16 * 1024 * 1024 )); then
    pass "At least 16 GiB RAM is installed ($(numfmt --from-unit=1024 --to=iec-i --suffix=B "$memory_kib" 2>/dev/null || printf '%s KiB' "$memory_kib"))."
else
    advisory 'Less than 16 GiB RAM is installed.'
fi

if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    pass "Graphical session detected (${XDG_SESSION_TYPE:-unknown})."
else
    advisory 'No graphical display was detected in this shell.'
fi

if command -v lspci >/dev/null 2>&1; then
    gpu="$(lspci | rg -i 'VGA compatible|3D controller|Display controller' | head -n 1 || true)"
    if [[ -n "$gpu" ]]; then
        pass "GPU detected: $gpu"
    else
        advisory 'No GPU was reported by lspci.'
    fi
fi

if command -v glxinfo >/dev/null 2>&1 && [[ -n "${DISPLAY:-}" ]]; then
    if gl_summary="$(glxinfo -B 2>&1)"; then
        renderer="$(printf '%s\n' "$gl_summary" | rg -m 1 'OpenGL renderer string' || true)"
        pass "OpenGL works: ${renderer:-renderer information unavailable}"
    else
        advisory "OpenGL check failed: $(printf '%s\n' "$gl_summary" | rg -m 1 '^(libGL error|Error:|X Error)' || printf '%s\n' "$gl_summary" | tail -n 1)"
    fi
fi

if [[ -f "$PREFIX_DIR/system.reg" ]]; then
    pass 'Dedicated Wine prefix is initialized.'
else
    advisory 'Dedicated Wine prefix is not initialized yet.'
fi

printf '\nResult: %d error(s), %d warning(s).\n' "$errors" "$warnings"
(( errors == 0 ))
