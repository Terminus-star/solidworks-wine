#!/usr/bin/env bash
# build-wine-portal.sh — optional: build CachyOS Wine 10.0 + Wine MR !10060
# (native file dialogs through the XDG desktop portal, e.g. KDE's picker).
#
# Same base as Arch/CachyOS's wine-cachyos-opt (tag cachyos-10.0-20260425-wine).
# Nothing is installed system-wide; move the result to /opt afterwards.
#
# Usage:
#   inplace/build-wine-portal.sh            (JOBS=N to change parallelism)
#   sudo mv build/portal/wine-cachyos-portal /opt/wine-cachyos-portal
#
# Environment overrides:
#   WORK   work directory (default <repo>/build/portal, ignored by git)
#   DEST   install directory (default $WORK/wine-cachyos-portal)
#   JOBS   make -j value (default: number of CPUs / 2)
#
# Fetches (if missing) into $WORK:
#   wine-cachyos-src/          git clone of CachyOS/wine-cachyos at TAG
#   aur-wine-cachyos-mr10060/  AUR recipe containing the rebased !10060 patch
# Logs: $WORK/logs/{generate,configure,make,install}.log
#
# Notes:
#   - MR !10060 was closed unmerged upstream and is LLM-generated; it is not
#     reviewed Wine code. Use at your own risk.
#   - Needs: git, mingw-w64-gcc, autoconf, perl, python, the usual Wine build
#     dependencies, and xdg-desktop-portal(-kde) at runtime.
#   - Gecko/Mono are copied from /opt/wine-cachyos (wine-cachyos-opt) if
#     installed; otherwise Wine offers to download them on first prefix use.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${WORK:-$REPO/build/portal}"
DEST="${DEST:-$WORK/wine-cachyos-portal}"
JOBS="${JOBS:-$(( $(nproc) / 2 ))}"
TAG="cachyos-10.0-20260425-wine"
SRC="$WORK/wine-cachyos-src"
AUR="$WORK/aur-wine-cachyos-mr10060"
PATCH="$AUR/mr10060-wine-cachyos-10.0.20260425.patch"
BUILD="$WORK/build"
LOGS="$WORK/logs"

if [[ -d "$DEST" ]] && [[ -n "$(ls -A "$DEST")" ]]; then
    echo "build: $DEST is not empty; refusing to install over it" >&2
    exit 1
fi
mkdir -p "$WORK" "$BUILD" "$LOGS"

# --- fetch inputs ---------------------------------------------------------------
if [[ ! -d "$SRC" ]]; then
    echo "build: fetching CachyOS Wine source ($TAG)"
    git clone --quiet --depth 1 --branch "$TAG" \
        https://github.com/CachyOS/wine-cachyos.git "$SRC"
fi
if [[ ! -f "$PATCH" ]]; then
    echo "build: fetching the AUR recipe with the !10060 patch"
    git clone --quiet https://aur.archlinux.org/wine-cachyos-mr10060.git "$AUR"
fi

# --- patch (once) ---------------------------------------------------------------
if git -C "$SRC" apply --reverse --check "$PATCH" 2>/dev/null; then
    echo "build: patch already applied"
else
    git -C "$SRC" apply "$PATCH"
    echo "build: patch applied"
fi

# --- generate sources -------------------------------------------------------------
# CachyOS's git tree doesn't ship configure and other generated files (Wine
# release tarballs do), so generate them as the AUR PKGBUILD's prepare() does.
# make_vulkan changes into its own directory, so -x/-X use the local XML.
if [[ ! -x "$SRC/configure" ]]; then
    echo "build: generating sources (log: $LOGS/generate.log)"
    ( cd "$SRC" && ./tools/make_requests && ./tools/make_specfiles \
        && ./dlls/winevulkan/make_vulkan -x vk.xml -X video.xml \
        && autoreconf -fiv ) > "$LOGS/generate.log" 2>&1
fi

# --- configure / build / install ----------------------------------------------------
# -Wno-incompatible-pointer-types: GCC 14+ makes that warning an error.
# -std=gnu17: safety net for GCC 15+'s C23 default.
flags="-O2 -pipe -std=gnu17 -Wno-incompatible-pointer-types"

echo "build: configure (log: $LOGS/configure.log)"
# configure must run from inside the build directory, hence the subshell.
( cd "$BUILD" && "$SRC/configure" \
    --prefix="$DEST" \
    --enable-archs=x86_64,i386 \
    --with-x --with-wayland --with-mingw \
    --with-freetype --with-gstreamer --with-alsa --with-ffmpeg \
    --without-oss --disable-lsteamclient --disable-tests \
    CFLAGS="$flags" CROSSCFLAGS="$flags" \
  > "$LOGS/configure.log" 2>&1 )

echo "build: make -j$JOBS (log: $LOGS/make.log) — this takes a while"
make -C "$BUILD" -j"$JOBS" > "$LOGS/make.log" 2>&1

echo "build: make install (log: $LOGS/install.log)"
make -C "$BUILD" install > "$LOGS/install.log" 2>&1

if [[ -d /opt/wine-cachyos/share/wine/gecko ]]; then
    mkdir -p "$DEST/share/wine"
    cp -a /opt/wine-cachyos/share/wine/gecko /opt/wine-cachyos/share/wine/mono "$DEST/share/wine/"
fi

echo "build: done — $("$DEST/bin/wine" --version 2>/dev/null)"
echo "next:  sudo mv '$DEST' /opt/wine-cachyos-portal"
