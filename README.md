# SOLIDWORKS 2026 on Linux: Reproducible Wine Compatibility Toolkit

An independent, experimental compatibility toolkit for **SOLIDWORKS 2026
SP03.2 and Wine 9.22**. It preserves the fixes, installation helpers, font
fallback, and no-splash desktop launcher developed on Linux Mint 21.3.

The project code is free to use and modify under MIT; Wine patches are LGPL
2.1-or-later and bundled Selawik fonts are OFL 1.1. No paid tool, AI account,
or cloud service is required. **SOLIDWORKS is not included or made free by this
project.** Bring your own lawful installer media and valid license, including
an eligible student license, and complete official activation yourself.
See [licensing](LICENSE.md) and [security](docs/SECURITY.md).

> **This fork** adds a second route that is tested with **SOLIDWORKS 2022**:
> run the copy that is already installed on your Windows partition (dual-boot)
> instead of installing it into Wine. Install steps are right below; how it
> works and known issues are in [inplace/README.md](inplace/README.md).
> The original 2026 install-into-Wine route follows further down.

## Install: run your existing Windows SOLIDWORKS

Tested: SOLIDWORKS 2022 SP02 on CachyOS (Arch), KDE Plasma 6, CachyOS Wine 10.0.
Run every command from the repository folder.

**You need**

- SOLIDWORKS installed on a Windows partition you can mount on Linux.
- A licence that works from this machine under Linux. A **network licence**
  (SolidNetWork, typical for universities) works as is if the server is
  reachable. A **standalone** licence must be activated again inside Wine.
- These packages (Arch/CachyOS names):

  ```bash
  sudo pacman -S --needed wine-cachyos-opt winetricks hivex icoutils \
      xdotool libnotify desktop-file-utils
  ```

**1. Mount the Windows partition read-write at `/mnt/windows`.**
Use your own partition name; for BitLocker, unlock it first (for example
`sudo cryptsetup open --type bitlk /dev/nvme0n1pX windows` and mount
`/dev/mapper/windows`).

```bash
sudo mkdir -p /mnt/windows
sudo mount /dev/nvme0n1pX /mnt/windows
```

Never boot Windows (VM or native) while it is mounted here, and turn off
Windows Fast Startup.

**2. Choose the Wine build.** Either the stock CachyOS Wine 10:

```bash
export WINE_BIN=/opt/wine-cachyos/bin/wine
```

or, for native KDE file dialogs, build the patched one (takes a while) and use it:

```bash
./inplace/build-wine-portal.sh
sudo mv build/portal/wine-cachyos-portal /opt/wine-cachyos-portal
export WINE_BIN=/opt/wine-cachyos-portal/bin/wine
```

Keep the same terminal open for the next steps (they use `WINE_BIN`).

**3. Create the Wine prefix and install the runtimes** (VC++, .NET 4.8, MSXML;
15–30 minutes, installer windows may appear):

```bash
export WINEPREFIX=~/.local/share/wineprefixes/solidworks-2022
./bin/setup-prefix.sh
```

**4. Link SOLIDWORKS into the prefix and import its registry:**

```bash
./inplace/sw-link.sh
./inplace/sw-reg-export.sh
./inplace/sw-reg-import.sh
```

`sw-reg-export.sh` only reads the Windows registry. It writes `./sw-registry/`,
which contains your licence server and settings — don't share it.

**5. Set the UI scale** (192 = 200 %; use 96 × your display scale):

```bash
"$WINE_BIN" reg add 'HKCU\Control Panel\Desktop' /v LogPixels /t REG_DWORD /d 192 /f
```

Only with the patched Wine from step 2 — turn on KDE's file picker:

```bash
"$WINE_BIN" reg add 'HKCU\Software\Wine\AppDefaults\SLDWORKS.exe\X11 Driver' \
    /v FileDialogPortal /t REG_SZ /d always /f
```

**6. Add the app-menu shortcut:**

```bash
./inplace/install-shortcut.sh
```

**7. KDE only — import the window rules** (fix focus jumping and a fullscreen
quirk): System Settings → Window Management → Window Rules → Import… →
`inplace/kwinrules-solidworks.kwinrule`.

**8. Start SOLIDWORKS** from the app menu ("SOLIDWORKS"), or run
`solidworks-2022`. The first start takes about a minute. Open your files
through the `W:` drive (`W:\Users\<you>\…`).

Always start it through the shortcut or `solidworks-2022`: it works around a
startup deadlock. Problems? See [troubleshooting](inplace/README.md#troubleshooting).

## Start here

- New machine: [step-by-step installation](docs/INSTALL.md).
- Already working: use the launcher below; do not reinstall to save source.
- AI agents: [AGENTS.md](AGENTS.md), [architecture](docs/ARCHITECTURE.md), and
  [reproducibility.json](reproducibility.json).
- Publish your copy: [GitHub setup and backup guide](docs/GITHUB.md).
- Contribute: [CONTRIBUTING.md](CONTRIBUTING.md).
- Problems: [troubleshooting](docs/TROUBLESHOOTING.md) and
  [validation limits](docs/VALIDATION.md).

## What has actually worked?

On the original Mint/Cinnamon X11 host: a successful core MSI installation,
an audit of 141 selected features and required files, Login Manager repair,
startup, a new empty Part document, and normal exit. Selawik removes the
missing-Segoe-UI warning without editing templates. The desktop launcher skips
the startup splash that triggered the desktop's unresponsive-window prompt.

This is **not yet a verified clean-install recipe across Linux distributions**.
The new source-build recipe is checksum-pinned and all five patches apply
cleanly, but a full clean Wine build followed by a fresh SOLIDWORKS installation
using this exact recipe still needs independent validation. Other releases,
Wayland-only sessions, ARM, add-ins, and real CAD workloads are unproven.
The vendor's [supported system requirements](https://www.solidworks.com/support/system-requirements)
do not include this Linux/Wine configuration. Keep a supported Windows setup
available for work you depend on.

## Everyday use after installation

From the cloned project directory:

```bash
./bin/run-solidworks.sh --no-splash

# Once, after configuring the runtime and prefix:
./bin/install-desktop-shortcut.sh
```

The generated desktop entry pins your clone's actual runtime and prefix paths.
It applies compatibility settings without storing a serial in the shortcut.
Keep that prefix between launches so legitimate application settings and
activation state can persist. If you move the clone, rebuild Wine for its new
location as needed and regenerate the shortcut. Do not copy activation state
to another person or machine.

No-splash uses the observed `/m` behavior **without a macro filename**. It is
undocumented as a splash switch and only applies to an otherwise empty launch.
Files and explicit macro arguments retain normal startup semantics.
Initialization still takes time; it is not a general speed fix.

## Source-only checks

These do not install or activate SOLIDWORKS:

```bash
./tests/static-check.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
./bin/build-helpers.sh              # Host GCC and both MinGW compilers required
python3 bin/build-wine-runtime.py --prepare-only   # Downloads pinned Wine source
python3 bin/audit-repository.py --staged           # Requires populated Git index
```

CI runs source tests and native-helper compilation, never the commercial
installer or activation. [Historical notes](docs/PROGRESS.md) retain the
investigation sequence; dated failures/pending actions there are historical,
not current instructions. Their private evidence paths are absent from Git.
