#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

scripts=(
    "$PROJECT_ROOT/bin/check-host.sh"
    "$PROJECT_ROOT/bin/install-desktop-shortcut.sh"
    "$PROJECT_ROOT/bin/install-vendor-prerequisites.sh"
    "$PROJECT_ROOT/bin/setup-prefix.sh"
    "$PROJECT_ROOT/bin/install-solidworks.sh"
    "$PROJECT_ROOT/bin/install-solidworks-direct.sh"
    "$PROJECT_ROOT/bin/build-helpers.sh"
    "$PROJECT_ROOT/bin/download-media.sh"
    "$PROJECT_ROOT/bin/prepare-payloads.sh"
    "$PROJECT_ROOT/bin/configure-download-prefix.sh"
    "$PROJECT_ROOT/bin/configure-fonts.sh"
    "$PROJECT_ROOT/bin/repair-login-manager.sh"
    "$PROJECT_ROOT/bin/run-solidworks.sh"
    "$PROJECT_ROOT/bin/winecfg.sh"
    "$PROJECT_ROOT/bin/diagnose.sh"
)

for script in "$PROJECT_ROOT/bin/common.sh" "${scripts[@]}"; do
    bash -n "$script"
done

for script in "${scripts[@]}"; do
    bash "$script" --help >/dev/null
done

test -s "$PROJECT_ROOT/assets/fonts/LICENSE.txt"
(cd "$PROJECT_ROOT/assets/fonts" && sha256sum --check SHA256SUMS >/dev/null)

if command -v shellcheck >/dev/null 2>&1; then
    shellcheck --external-sources --source-path=SCRIPTDIR \
        "$PROJECT_ROOT"/bin/*.sh "$PROJECT_ROOT"/tests/*.sh
fi

# Source checks intentionally do not depend on the developer's runtime/prefix.

# A serial-shaped value must never be checked into this project.
if rg -l --glob '*.sh' --glob '*.md' --glob '*.py' --glob '*.c' \
    '[0-9]{16}[[:alnum:]]{8}' "$PROJECT_ROOT/bin" "$PROJECT_ROOT/lib" \
    "$PROJECT_ROOT/native" "$PROJECT_ROOT/tests" "$PROJECT_ROOT/docs" "$PROJECT_ROOT/README.md"; then
    printf 'A possible serial number was found in a project file.\n' >&2
    exit 1
fi

printf 'static checks: PASS\n'
