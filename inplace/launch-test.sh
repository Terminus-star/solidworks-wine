#!/usr/bin/env bash
# launch-test.sh — measure the startup deadlock: N launches through
# inplace/solidworks-2022, alternating pinned / unpinned, each stopped once it
# reaches the main window, deadlocks, or times out.
#
# Usage:
#   inplace/launch-test.sh [N]      (default N=10)
#
# Uses the same WINE_BIN / PREFIX overrides as the launcher. Tracing is on
# (+loaddll,+module,+seh) so a deadlock is recognised and its log shows which
# DLL load or lookup each stuck thread was in. Logs land in the launcher's
# log directory; results are appended to ./launch-tests.tsv.
#
# SOLIDWORKS windows open and close by themselves while this runs, and every
# Wine process in the prefix is killed between runs — save your work first.

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
N="${1:-10}"
WINE_BIN="${WINE_BIN:-/opt/wine-cachyos-portal/bin/wine}"
PREFIX="${PREFIX:-$HOME/.local/share/wineprefixes/solidworks-2022}"
WINESERVER_BIN="$(dirname "$WINE_BIN")/wineserver"
TSV="$PWD/launch-tests.tsv"
export WINE_BIN PREFIX
export WINEDEBUG="${WINEDEBUG:-+loaddll,+module,+seh}"

stop_prefix() {
    WINEPREFIX="$PREFIX" "$WINESERVER_BIN" -k 2>/dev/null
    sleep 3
}

[[ -f "$TSV" ]] || printf 'run\tmode\tresult\tseconds\tlog\n' > "$TSV"
for (( i = 1; i <= N; i++ )); do
    # Odd runs pinned, even runs unpinned, so both see the same conditions.
    if (( i % 2 )); then mode=pin; unset NO_PIN; else mode=nopin; export NO_PIN=1; fi
    stop_prefix
    # Launcher output: "solidworks: <result> after <N>s (log: <path>)"
    line=$("$HERE/solidworks-2022" 2>&1 | grep '^solidworks:')
    read -r _ result _ secs _ log <<< "$line"
    printf '%s\t%s\t%s\t%s\t%s\n' "$i" "$mode" "$result" "${secs%s}" "${log%)}" | tee -a "$TSV"
    stop_prefix
done
echo
echo "Summary (mode, result, count):"
tail -n +2 "$TSV" | cut -f2,3 | sort | uniq -c
