# Installation on a new Linux system

## 0. Scope and stop conditions

Target: x86-64 Linux with 32-bit userspace, X11, SOLIDWORKS **2026 SP03.2**,
English media, and patched **Wine 9.22**. The original application worked on
Mint 21.3; this newly assembled clean-build workflow has not been run end-to-end
on a fresh machine. Treat it as a reproduction recipe to validate, not a
support guarantee. Read [security](SECURITY.md), [validation](VALIDATION.md),
and [architecture](ARCHITECTURE.md) first.

Use an ordinary graphical desktop user, never sudo for Wine/project scripts.
Only host package installation below needs administrator privileges. Do not
overwrite an existing prefix/runtime or stop an application with unsaved work.
Have your own complete licensed media, serial, and vendor account/access ready.
Review and accept vendor license terms yourself. A student license is an
entitlement, not a mode this project can grant or bypass.

## 1. Clone and set local paths

Clone the published repository using its GitHub **Code → HTTPS** URL, then
open a terminal in that clone. No GitHub account is needed to download a public
repository. Prefer a permanent path on a local Linux filesystem. Avoid unusual
characters in the Wine build path: desktop quoting is tested, but upstream
build tools can have stricter path assumptions.

```bash
# Run from the cloned solidworks-wine directory.
cp -n config.example.sh config.local.sh
```

Edit `config.local.sh` in a text editor. Point `SOLIDWORKS_FULL_MEDIA_DIR` at
the complete downloaded media directory, not just the bootstrapper. Then:

```bash
source ./config.local.sh
```

This file is not auto-executed. Source it in each new terminal when using
nondefault paths. Do not add credentials. Defaults are `prefix/`, `wine-runtime/`,
`full-media/`, `serial.txt`, and `logs/` inside the clone. The media environment
override avoids having to copy the media or replace an existing symlink.

## 2. Install host dependencies

Core Python uses Python 3.10+ and its standard library. Source tests need Bash,
Git, ripgrep, GCC, and GNU utilities. Helpers need i686 and x86_64 MinGW GCC.
Wine needs development libraries for **both 64-bit and 32-bit** Linux, including
graphics, fonts, and TLS.

Ubuntu 22.04 / Mint 21.x starting package list: review the package manager's
proposed changes before accepting. Packages may differ on newer distributions.

```bash
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install build-essential gcc-multilib g++-multilib \
  gcc-mingw-w64-i686 gcc-mingw-w64-x86-64 \
  git ripgrep python3 python3-venv p7zip-full unzip patch flex bison pkg-config \
  winetricks cabextract curl xz-utils \
  xdg-user-dirs libglib2.0-bin desktop-file-utils \
  libx11-dev libx11-dev:i386 libxext-dev libxext-dev:i386 \
  libxrender-dev libxrender-dev:i386 libxrandr-dev libxrandr-dev:i386 \
  libxi-dev libxi-dev:i386 libxcursor-dev libxcursor-dev:i386 \
  libxfixes-dev libxfixes-dev:i386 libxinerama-dev libxinerama-dev:i386 \
  libfreetype-dev libfreetype-dev:i386 \
  libgl-dev libgl-dev:i386 libgnutls28-dev libgnutls28-dev:i386 \
  libasound2-dev libasound2-dev:i386 libpulse-dev libpulse-dev:i386 \
  libdbus-1-dev libdbus-1-dev:i386 libfontconfig-dev libfontconfig-dev:i386
```

Install matching 32-bit graphics runtimes for your GPU. Do not blindly replace
proprietary drivers with Mesa packages. Optional Wine features can need further
development packages; inspect configure warnings and your workload needs.
60 GiB free is a planning starting point, not an upper bound for media, two
Wine builds, a prefix, and backups. Meet the vendor's RAM/graphics requirements.

For Fedora, Arch, openSUSE, or newer Ubuntu/Mint, translate dependencies into
that distribution's multilib/devel packages. These are **porting targets**, not
tested entries. Do not substitute new Wine or a new-WoW64-only build and assume
the 32-bit Unix MSI patches apply. Consult Wine's
[build documentation](https://gitlab.winehq.org/wine/wine/-/wikis/Building-Wine)
and the pinned source's `README.md` and `configure --help`.

## 3. Build private patched Wine

```bash
./tests/static-check.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
./bin/build-helpers.sh
python3 bin/build-wine-runtime.py --prepare-only
```

Preparation downloads official Wine 9.22, checks the manifest's SHA-256, applies
five patches with zero fuzz, and prints exact build commands. To use a local
archive, add `--source-archive /absolute/path/to/wine-9.22.tar.xz`; the same hash
is required. Cached source is under `build/repro-wine/`. Do not manually change
that tree and treat the patch stamp as a complete tree-integrity guarantee.

When ready for a potentially hours-long build:

```bash
python3 bin/build-wine-runtime.py --build --jobs 4
./wine-runtime/bin/wine --version
./bin/check-host.sh
```

The recipe builds 64-bit PE modules, then 32-bit Unix/Winelib modules using
`--with-wine64` and `--without-mingw`, then installs both privately. It keeps
X11/OpenGL/FreeType/GnuTLS enabled. Each step has a two-hour default limit;
adjust `--step-timeout` deliberately on slower hardware. Logs are in
`build/repro-wine/step-N.log`. Interruptions stop that build process group,
not running desktop applications.

A nonempty runtime is refused. For an independent rebuild, use new `--work-dir`
and `--runtime-dir` paths, then set `WINE_BIN` to its absolute `bin/wine` path.
Keep the old runtime until the new one is validated. No system Wine files are
replaced. The original runtime was assembled differently; this clean recipe
still needs full build-and-application validation.

## 4. Initialize the dedicated prefix

```bash
./bin/setup-prefix.sh
```

This installs Winetricks corefonts, vcrun2010, vcrun2022, msxml3, msxml6, and
dotnet48, then sets Windows 11 mode. Winetricks downloads upstream packages
into its normal cache. Its recipes/downloads can change: this is not fully
offline or bit-for-bit reproducible. Record `winetricks --version` privately.
Do not substitute arbitrary DLLs for failing prerequisites.

`--minimal` and `--no-dotnet` are diagnostic options, not a complete setup.
The media may contain .NET 4.8.1; the working prefix used **4.8**. Wine Mono is
not treated as a replacement. Follow Wine's normal Gecko prompt if needed.
After a timeout inspect processes before retrying; do not erase the prefix.

## 5. Supply complete media and inspect plans

Expected layout:

```text
your-media-directory/
  PreReqs/VBA/vba71.msi
  PreReqs/VBA/vba71_1033.msi
  PreReqs/VSTA17/vsta_setup.exe
  swcef/CEF for SOLIDWORKS Applications.msi
  swloginmgr/SOLIDWORKS Login Manager.msi
  swwi/data/solidworks.msi
  swwi/data/1033.mst
  swwi/data/spatialiop.zip
  swwi/data/... vendor cabinets and Toolbox archives ...
```

Use the vendor/school's authorized channel, including Toolbox. A complete
download from the vendor's supported Windows environment is the simplest
input. The optional Linux downloader is in
[troubleshooting](TROUBLESHOOTING.md#black-installation-manager).

```bash
./bin/install-vendor-prerequisites.sh --plan
./bin/install-solidworks-direct.sh --plan
```

Confirm ProductCode `{6172DDB3-98E6-46E1-A0C1-DB8FD05063EF}`, ProductVersion
`34.132.0003`, and 2026 SP03.2. The core install rejects another product/version.
Its plan reads real feature tables and lists missing Toolbox archives. Do not
rename another release's media to make it appear compatible.

## 6. Vendor prerequisites and private serial

After reviewing vendor terms and closing all programs in this prefix:

```bash
./bin/install-vendor-prerequisites.sh --install
python3 bin/set-serial.py
```

The prerequisite runner installs provided VBA x64/English packages, VSTA 2022,
and CEF sequentially with prefix locking, time bounds, and private logs. MSI
results and product states are verified; VSTA currently checks bootstrapper
exit only. The new runner has not itself been used for a clean prerequisite
installation. The original prefix had VBA 7.1.11.35, VSTA 17.0.33529, and CEF
147.0.34792.0; their presence does not prove every integration works.

The hidden serial prompt creates an owner-only `serial.txt`. Existing files
are preserved unless `--replace` is explicit. Never put a real serial in
arguments or issues. Format validation is not entitlement/activation validation.

## 7. Install and verify the core application

```bash
./bin/install-solidworks-direct.sh
./bin/install-solidworks-direct.sh --verify
```

The controller selects core MSI features, checks Toolbox, pre-extracts Spatial
IOP, audits every Spatial member's existence/size, and stages Scheduler
resources before registration. The serial goes privately via stdin to the MSI
helper. Builtin MSXML is selected only for this installation path; do not turn
that into a global app-launch override.

Private evidence goes in `logs/install-TIMESTAMP/`. Defaults: 30 minutes total,
four minutes without observed progress, 256 MiB logs, four CPU affinity, and
reduced priority. Adjust `--timeout SECONDS` / `--idle-timeout SECONDS` only
after investigating. The watchdog can stop this dedicated prefix's Wine server.

Success automatically triggers Login Manager repair after the core lock is
released. To repeat only that repair, close SOLIDWORKS and run
`./bin/repair-login-manager.sh`. Require file/feature verification, not just an
MSI product record. Startup and activation remain separate gates.

## 8. Fonts, shortcut, and activation

```bash
./bin/configure-fonts.sh
./bin/install-desktop-shortcut.sh
./bin/run-solidworks.sh --no-splash
```

Font setup installs checksummed, unmodified Selawik and a prefix-local missing
Segoe UI alias. It backs up registry settings and leaves documents/templates
alone. It is a substitute; typography can differ. A genuine licensed Segoe UI
installation takes precedence.

The shortcut uses the XDG desktop directory and a generic engineering icon on
fresh clones. If unavailable, use `--desktop-dir /absolute/desktop/path`.
Different existing shortcuts are preserved unless `--replace` requests a
backup/replacement. Some desktops require right-click → Allow Launching / Trust;
others don't display desktop icons. Use the shell launcher in that case.

Complete official activation/registration with your own license. This project
does not fill personal details, grant entitlement, renew licenses, suppress
activation, or copy another user's license. Keep using the same prefix so
legitimate application settings persist.

## 9. Acceptance test and future updates

Check startup, create a new empty part, confirm no missing-font warning, close
normally, reopen, and check settings persist. Then save/reopen a disposable
model and test the CAD operations you need. Record separate results using
[the validation checklist](VALIDATION.md); an empty part is not production proof.

Before updates, close the application and keep a private recoverable backup of
your own state. Review Git changes before running scripts. Source updates do
not require prefix recreation or serial re-entry. Never merge a new runtime
build over a working one automatically.
