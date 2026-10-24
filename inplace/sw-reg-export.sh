#!/usr/bin/env bash
# sw-reg-export.sh — export SOLIDWORKS' registry entries from an offline
# (not running) Windows install into .reg files for `wine regedit`.
#
# Usage:
#   inplace/sw-reg-export.sh
#
# Environment overrides:
#   WIN_ROOT   mounted Windows partition   (default /mnt/windows)
#   WIN_USER   Windows profile folder name (default: the only profile under
#              $WIN_ROOT/Users besides Default/Public; set it if there are more)
#   OUT        output directory            (default ./sw-registry)
#
# Only reads the hive files (hivexregedit --export never writes to them).
# Writes to $OUT/:
#   hklm-vendor.reg   HKLM\SOFTWARE\{SolidWorks,Dassault Systemes,...}
#   hkcu-vendor.reg   HKCU\Software\{SolidWorks,...}  (per-user settings)
#   hklm-com.reg      SOLIDWORKS' COM registrations from HKLM\SOFTWARE\Classes
#   com-roots.txt     which Classes subtrees were picked, for review
#   import/*.reg      UTF-16LE copies of the three .reg files — import these
#
# The output contains your licence server address and personal settings:
# never commit it (sw-registry/ is in .gitignore).
#
# Licensing: `FLEXlm License Manager` IS exported — for a network licence it
# only holds SW_D_LICENSE_FILE (port@server), which is not machine-bound.
# Deliberately NOT exported: Macrovision keys and ProgramData\FLEXnet
# (standalone activation data, machine-bound; re-activate inside Wine).
#
# Limits:
#   - .NET COM classes that live only in the Windows GAC (no CodeBase path)
#     are registered here, but their assemblies are not copied.
#   - Keys are found by name/value text (solidworks|sldworks|edrawings|
#     dassault); anything SOLIDWORKS registered without those words is missed.

set -euo pipefail

WIN_ROOT="${WIN_ROOT:-/mnt/windows}"
OUT="${OUT:-$PWD/sw-registry}"
SOFTWARE_HIVE="$WIN_ROOT/Windows/System32/config/SOFTWARE"

if [[ -z "${WIN_USER:-}" ]]; then
    mapfile -t profiles < <(find "$WIN_ROOT/Users" -mindepth 1 -maxdepth 1 -type d \
        ! -iname 'Default*' ! -iname 'Public' ! -iname 'All Users' -printf '%f\n')
    if (( ${#profiles[@]} == 1 )); then
        WIN_USER="${profiles[0]}"
    else
        echo "sw-reg-export: set WIN_USER to one of: ${profiles[*]:-<none found>}" >&2
        exit 1
    fi
fi
USER_HIVE="$WIN_ROOT/Users/$WIN_USER/NTUSER.DAT"

# Hive files store keys without their root; --prefix puts it back so the
# output has full names like [HKEY_LOCAL_MACHINE\SOFTWARE\SolidWorks].
HKLM='HKEY_LOCAL_MACHINE\SOFTWARE'
HKCU='HKEY_CURRENT_USER'
REG_HEADER=$'Windows Registry Editor Version 5.00\n'
MATCH='solidworks|sldworks|edrawings|dassault'

mkdir -p "$OUT"

for hive in "$SOFTWARE_HIVE" "$USER_HIVE"; do
    [[ -f "$hive" ]] || { echo "missing hive: $hive (is $WIN_ROOT mounted?)" >&2; exit 1; }
done

# export_key <hive> <prefix> <key>
# Print one subtree as .reg text, minus the header line. Missing keys are
# reported and skipped (with pipefail, a hivexregedit error fails the pipe).
export_key() {
    if ! hivexregedit --export --prefix "$2" "$1" "$3" 2>/dev/null | tail -n +2; then
        echo "  skipped (not found): $3" >&2
    fi
}

# --- 1. Vendor keys: copied whole -------------------------------------------
echo "Exporting vendor keys..."
{
    echo "$REG_HEADER"
    for key in '\SolidWorks' '\Dassault Systemes' '\eDrawings' '\Srac' \
               '\FLEXlm License Manager' \
               '\WOW6432Node\SolidWorks' '\WOW6432Node\Dassault Systemes' \
               '\WOW6432Node\FLEXlm License Manager'; do
        export_key "$SOFTWARE_HIVE" "$HKLM" "$key"
    done
} > "$OUT/hklm-vendor.reg"

{
    echo "$REG_HEADER"
    for key in '\Software\SolidWorks' '\Software\Dassault Systemes' \
               '\Software\eDrawings' '\Software\Srac'; do
        export_key "$USER_HIVE" "$HKCU" "$key"
    done
} > "$OUT/hkcu-vendor.reg"

# --- 2. COM: pick SOLIDWORKS' subtrees out of Classes -----------------------
# Pass 1 reads a human-readable export (strings as text) and decides which
# subtrees under Classes belong to SOLIDWORKS. Output: one path per line,
# relative to Classes, e.g. "CLSID\{...}" or "Wow6432Node\TypeLib\{...}".
echo "Pass 1: finding SOLIDWORKS COM entries in Classes..."
hivexregedit --export --unsafe-printable-strings --prefix "$HKLM" \
    "$SOFTWARE_HIVE" '\Classes' 2>/dev/null \
| awk -v match_re="$MATCH" '
    BEGIN { base = "HKEY_LOCAL_MACHINE\\SOFTWARE\\Classes\\" }

    # Key line: [HKEY_LOCAL_MACHINE\SOFTWARE\Classes\CLSID\{...}\InprocServer32]
    /^\[/ {
        rel = substr($0, 2, length($0) - 2)
        rel = substr(rel, length(base) + 1)
        # The 32-bit view lives under Wow6432Node\; keep it as a prefix.
        wow = ""
        if (tolower(substr(rel, 1, 12)) == "wow6432node\\") {
            wow = substr(rel, 1, 12); rel = substr(rel, 13)
        }
        n = split(rel, p, "\\")
        top = tolower(p[1])
        next
    }

    # Value line: @=str(1):"data"  or  "Name"=str(1):"data"  or  dword:...
    /^(@|")/ {
        name = ($0 ~ /^@=/) ? "@" : substr($0, 2, index(substr($0, 2), "\"") - 1)
        data = $0
        sub(/^(@|"[^"]*")=/, "", data)
        if (data ~ /^str\([12]\):"/) { sub(/^str\([12]\):"/, "", data); sub(/"$/, "", data) }
        hit = tolower(data) ~ match_re

        if (top == "clsid" && n >= 2) {
            root = wow "CLSID\\" p[2]
            if (hit) picked[root] = 1
            if (n == 2 && name == "AppID") appid_of[root] = data
        } else if (top == "typelib" && n >= 2) {
            if (hit) picked[wow "TypeLib\\" p[2]] = 1
        } else if (top == "interface" && n == 3 && tolower(p[3]) == "typelib" && name == "@") {
            iface_tl[wow "Interface\\" p[2]] = tolower(data)
        } else if (n == 2 && tolower(p[2]) == "clsid" && name == "@" && top !~ /^(appid|interface)$/) {
            progid_clsid[wow p[1]] = tolower(data)        # ProgID -> CLSID
        } else if (n == 1 && wow == "" && substr(p[1], 1, 1) == "." && name == "@") {
            ext_progid[p[1]] = tolower(data)              # .ext -> ProgID
        }
    }

    # Follow references from the directly-matched CLSIDs and TypeLibs.
    function last(path,   q, k) { k = split(path, q, "\\"); return tolower(q[k]) }
    END {
        for (r in picked) {
            if (r ~ /CLSID\\/)   { clsid[last(r)] = 1; nclsid++ }
            if (r ~ /TypeLib\\/) { tlib[last(r)] = 1;  ntlib++ }
        }
        for (i in iface_tl)     if (iface_tl[i] in tlib)      { picked[i] = 1; niface++ }
        for (x in progid_clsid) if (progid_clsid[x] in clsid) { picked[x] = 1; progid[tolower(x)] = 1; nprog++ }
        for (e in ext_progid)   if (ext_progid[e] in progid)  { picked[e] = 1; next_++ }
        for (r in appid_of)     if (r in picked)              { picked["AppID\\" appid_of[r]] = 1; napp++ }
        for (r in picked) print r
        printf "  CLSIDs %d, TypeLibs %d, Interfaces %d, ProgIDs %d, extensions %d, AppIDs %d\n", \
            nclsid, ntlib, niface, nprog, next_, napp > "/dev/stderr"
    }
' | sort > "$OUT/com-roots.txt"

# Pass 2 reads the exact (hex) export and keeps a key if it, or any parent
# key, is listed in com-roots.txt. Comparison ignores case, like Windows.
echo "Pass 2: exporting the picked subtrees..."
{
    echo "$REG_HEADER"
    hivexregedit --export --prefix "$HKLM" "$SOFTWARE_HIVE" '\Classes' \
    | awk '
        BEGIN { base = "HKEY_LOCAL_MACHINE\\SOFTWARE\\Classes\\" }
        FNR == NR { want[tolower($0)] = 1; next }
        /^\[/ {
            r = tolower(substr($0, 2, length($0) - 2))
            r = substr(r, length(base) + 1)
            keep = 0
            while (r != "") {
                if (r in want) { keep = 1; break }
                if (!match(r, /\\[^\\]*$/)) break
                r = substr(r, 1, RSTART - 1)
            }
        }
        keep { print }
    ' "$OUT/com-roots.txt" -
} > "$OUT/hklm-com.reg"

# --- 3. UTF-16 copies for importing -------------------------------------------
# Wine's regedit treats a .reg file as Unicode only if it starts with the
# UTF-16LE byte-order mark FF FE (programs/regedit/regproc.c). Otherwise it
# reads hex(1)/hex(2)/hex(7) string data as one-byte text and widens every
# byte, so "SldPart" would be stored as "S\0l\0d\0...". Windows' own regedit
# writes Version 5.00 files as UTF-16LE with that mark, so we do the same.
# The ASCII files above stay as the readable, grep-able copies.
mkdir -p "$OUT/import"
for f in hklm-vendor.reg hkcu-vendor.reg hklm-com.reg; do
    { printf '\xff\xfe'; iconv -f UTF-8 -t UTF-16LE "$OUT/$f"; } > "$OUT/import/$f"
done

# --- 4. Summary ---------------------------------------------------------------
echo
echo "Keys exported:"
for f in hklm-vendor.reg hkcu-vendor.reg hklm-com.reg; do
    printf '  %-16s %6d keys  %s\n' "$f" "$(grep -c '^\[' "$OUT/$f")" \
        "$(du -h "$OUT/$f" | cut -f1)"
done
echo "Picked COM roots: $(wc -l < "$OUT/com-roots.txt") (see com-roots.txt)"
echo "Results in $OUT/  — next: inplace/sw-reg-import.sh"
