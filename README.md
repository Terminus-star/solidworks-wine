# SOLIDWORKS 2026 on Linux / Wine

An independent, experimental compatibility toolkit for **SOLIDWORKS 2026
SP03.2 and Wine 9.22**. It preserves the fixes, installation helpers, font
fallback, and no-splash desktop launcher developed on Linux Mint 21.3.

The project code is free to use and modify under MIT; Wine patches are LGPL
2.1-or-later and bundled Selawik fonts are OFL 1.1. No paid tool, AI account,
or cloud service is required. **SOLIDWORKS is not included or made free by this
project.** Bring your own lawful installer media and valid license, including
an eligible student license, and complete official activation yourself.
See [licensing](LICENSE.md) and [security](docs/SECURITY.md).

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
