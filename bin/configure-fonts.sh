#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SCRIPT_DIR/common.sh"
if [[ "${1:-}" == '--help' ]]; then
    printf 'Usage: configure-fonts.sh\nInstall bundled Selawik fonts and a prefix-local Segoe UI fallback.\nClose SOLIDWORKS first; no templates or font files are renamed.\n'
    exit 0
fi
[[ $# == 0 ]] || die 'Unexpected argument. Use --help.'
prepare_wine_environment
require_prefix
require_executable "$WINE_BIN" wine
require_executable "$PROJECT_ROOT/build/font-probe.exe" 'Font probe (run bin/build-helpers.sh)'
exec 9>"$PREFIX_DIR/.solidworks-install.lock"
flock -n 9 || die 'Another controller is using this prefix.'
PYTHONPATH="$PROJECT_ROOT/lib" python3 -c \
    'import os; from pathlib import Path; from solidworks_wine.supervisor import ensure_idle; ensure_idle(Path(os.environ["WINEPREFIX"]))'

assets="$PROJECT_ROOT/assets/fonts"
destination="$PREFIX_DIR/drive_c/windows/Fonts"
font_key='HKLM\Software\Microsoft\Windows NT\CurrentVersion\Fonts'
alias_key='HKCU\Software\Wine\Fonts\Replacements'
files=(selawk.ttf selawkb.ttf selawkl.ttf selawksb.ttf selawksl.ttf)
names=('Selawik' 'Selawik Bold' 'Selawik Light' 'Selawik Semibold' 'Selawik Semilight')
(cd "$assets" && sha256sum --check SHA256SUMS)
[[ -s "$assets/LICENSE.txt" ]] || die 'Bundled font license is missing.'

# Refuse to overwrite different font binaries, and retain the previous
# registry configuration before changing any registrations or aliases.
for filename in "${files[@]}"; do
    if [[ -e "$destination/$filename" ]]; then
        cmp -s "$assets/$filename" "$destination/$filename" || die "Different existing font: $destination/$filename"
    fi
done
mkdir -p "$LOG_DIR" "$destination"
backup_dir="$(mktemp -d "$LOG_DIR/fonts-XXXXXXXX")"
timeout 20 "$WINE_BIN" reg export "$font_key" "$backup_dir/font-registrations.reg" /y
if timeout 20 "$WINE_BIN" reg query "$alias_key" >/dev/null 2>&1; then
    timeout 20 "$WINE_BIN" reg export "$alias_key" "$backup_dir/font-replacements.reg" /y
fi

for index in "${!files[@]}"; do
    install -m 0644 "$assets/${files[$index]}" "$destination/${files[$index]}"
    timeout 20 "$WINE_BIN" reg add "$font_key" /v "${names[$index]} (TrueType)" /t REG_SZ /d "${files[$index]}" /f
done
install -m 0644 "$assets/LICENSE.txt" "$destination/Selawik-LICENSE.txt"

# Wine's family replacement enumerates the alias as an available family;
# a FontSubstitutes entry alone would still leave SOLIDWORKS warning that
# the named template font was missing. A real Segoe UI takes precedence.
timeout 20 "$WINE_BIN" reg add "$alias_key" /v 'Segoe UI' /t REG_SZ /d Selawik /f
timeout 20 "$WINE_BIN" "$PROJECT_ROOT/build/font-probe.exe" 'Segoe UI'
note "Installed prefix-local Selawik fallback. Previous font registrations: $backup_dir"
note 'Restart SOLIDWORKS to refresh its font list. Templates remain unchanged.'
