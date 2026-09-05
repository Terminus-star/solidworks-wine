# Validation and support boundaries

## Known baseline

Historical host: Linux Mint 21.3, x86_64, Cinnamon/X11, AMD RX 5600-series GPU,
Wine 9.22 with private compatibility modules, SOLIDWORKS 2026 SP03.2 English.
Observed on September 4, 2026: core MSI success, 141 selected feature audit,
required core files, Login Manager repair, main workspace, empty new part, and
normal close. Later font fallback and no-splash launches worked on that host.
The user's latest report was that operation worked well except startup splash.

This does not certify permanent activation, all add-ins, rendering correctness,
file interchange, assemblies, simulation, PDM, or production workloads.
Activation is user-specific and must not be inferred from the student title,
an installed-product registry record, or a grace-period launch.

## Packaging validation versus application validation

Source packaging checks on September 4, 2026: **33/33 tests passed**, ShellCheck
0.8.0/static checks passed, and all six maintained native helpers compiled with
warnings treated as errors. A separate source-only export in a path containing
spaces passed the same tests and helper build, all five zero-fuzz Wine patches,
and the whole-index publication audit. The desktop round-trip test used GLib's
actual launcher parser with spaces, Unicode, percent signs, and quoted shell
metacharacters; it launched a harmless test stub, not SOLIDWORKS. No user prefix
or licensed application was installed, activated, or restarted for these checks.

The source-package work verifies source tests, native-helper compilation, the
official Wine archive hash, and zero-fuzz patch application. Tests run against
mock launchers, temporary directories, and fake credentials, not real licensing.
The generated desktop entry uses standard freedesktop escaping.

The **new full runtime build recipe and vendor-prerequisite runner have not
been tested end-to-end in a fresh Wine/SOLIDWORKS installation**. The original
runtime was assembled from existing host builds and patched modules. Source
portability checks cannot establish that the new recipe reproduces every
prerequisite or build feature. Wine/Winetricks host dependencies and vendor
downloads are not fully pinned; the project is not bit-for-bit reproducible.

| Environment | Status |
| --- | --- |
| Original Mint 21.3 / X11 host | Historical installation and empty-part smoke test passed |
| Fresh Mint 21.x / Ubuntu 22.04 | Documented recipe; full clean build/install still needed |
| Ubuntu 24.04 and other x86_64 Linux | Source CI target or porting target, not application-certified |
| Wayland-only, ARM, other Wine/SOLIDWORKS versions | Unvalidated, outside the baseline |

## Community result checklist

Copy this into a compatibility report; do not include usernames, serials,
activation screenshots, private model data, raw logs, or account/session URLs.

```text
Repository commit:
Distro/release and CPU architecture:
Desktop and X11/Wayland:
GPU and driver version:
Wine version and clean build vs existing runtime:
Winetricks version:
SOLIDWORKS release/language (no serial):
Source tests and helper compilation: PASS / FAIL / NOT RUN
Pinned archive and five patches: PASS / FAIL / NOT RUN
Full 64-bit + 32-bit runtime build: PASS / FAIL / NOT RUN
Fresh prefix prerequisites: PASS / FAIL / NOT RUN
VBA / VSTA / CEF installation: PASS / FAIL / NOT RUN
Core MSI result and file/feature audit: PASS / FAIL / NOT RUN
Login Manager repair: PASS / FAIL / NOT RUN
Official activation: confirmed by user / not confirmed (no identifiers)
Main window / new part / normal exit: PASS / FAIL / NOT RUN
Font fallback and no-splash behavior: PASS / FAIL / NOT RUN
Settings survive restart: PASS / FAIL / NOT RUN
Save/reopen disposable model and representative operations:
Known failures / optional components not tested:
```

Prefer a genuinely new, separately located test prefix. Preserve your working
installation and backups. Submit source-level fixes and sanitized summaries;
do not upload entire Wine prefixes to demonstrate success.
