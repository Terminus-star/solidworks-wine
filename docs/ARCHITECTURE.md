# Architecture and agent map

## Execution flow

```text
manifest + Wine source + patches → private runtime
helper C source                 → build/ Windows probes and MSI helper
own vendor media + prerequisites + own private serial
  → dedicated prefix → MSI plan → payload audit → bounded install
  → file/feature verification → Login Manager repair
  → font configuration → per-machine desktop entry
  → user activation → application/CAD validation
```

The prefix is persistent local application state, not a build artifact to
publish. The runtime is compiled against the host; Git preserves its recipe,
not a portable copy of a working installation.

## Ownership map

| Location | Responsibility |
| --- | --- |
| `reproducibility.json` | Target versions, source hash, ordered patches, workflow and evidence limits |
| `bin/common.sh` | Paths, private Wine environment, payload staging, bounded server wait |
| `bin/build-wine-runtime.py` | Verified source acquisition, zero-fuzz patches, bounded local build |
| `bin/setup-prefix.sh` | Winetricks prerequisites and Windows 11 mode |
| `bin/install-vendor-prerequisites.*` | Explicit VBA/VSTA/CEF installation with private evidence |
| `bin/install-solidworks-direct.sh` | Thin CLI, installer-only MSXML override, Login Manager follow-up |
| `bin/install-controller.py` | Plan/install/verify orchestration and evidence records |
| `lib/solidworks_wine/msi.py` | Actual MSI table queries, core feature selection, release gate |
| `lib/solidworks_wine/supervisor.py` | Prefix lock, busy-process check, watchdog, bounded logs |
| `lib/solidworks_wine/verification.py` | Product/features, component keypaths, required installed files |
| `lib/solidworks_wine/media.py` | Toolbox completeness and all-member Spatial existence/size audit |
| `lib/solidworks_wine/credentials.py` | Serial input and serial-specific log redaction |
| `lib/solidworks_wine/downloads.py` | Vendor-authorized package requests and bounded transfers |
| `native/msi-tool.c` | Windows Installer API queries/install; licensed serial through stdin |
| `native/` | Source for COM, header-layout, font, window and vendor-checksum probes |
| `bin/run-solidworks.sh` | Persistent-prefix app launch, no-splash and diagnostic software rendering |
| `bin/configure-fonts.sh` | Verified Selawik assets and prefix-only missing-family replacement |
| `lib/solidworks_wine/desktop.py` | Freedesktop quoting and path-specific launcher generation |
| `bin/audit-repository.py` | Whole-index publication audit, including actual staged file contents |

Legacy experiment source in `tests/*.c`, `tests/*.cpp`, `tests/*.vbs`, and two
`bin/*.c` files remains as reference. The maintained native helper build is
`bin/build-helpers.sh`; legacy experiments are not all part of CI.

## Why each Wine patch exists

| Patch | Compatibility behavior / boundary |
| --- | --- |
| `wine-windows-ui-text-scale.patch` | UISettings supports IAgileObject and normal text scale for the web installer |
| `wine-urlmon-msxml-stream.patch` | Native MSXML receives readable streams; sync binding is environment-gated |
| `wine-wininet-response-seek.patch` | Preserves prefetched HTTP bytes when a response stream is rewound |
| `wine-msi-solidworks-actions.patch` | Exact product/action/status registration exceptions; replaces dead custom-action server; guarded Spatial extraction skip |
| `wine-comctl32-header-layout.patch` | Guards invalid header-layout pointers that caused startup crashes |

The MSI patch does not authorize a license or skip activation. Accepting an
exception is also not proof that registration completed correctly: independently
verify product features, COM/runtime behavior, and the application. Do not widen
product IDs or exception acceptance to make another release appear successful.
The Python controller audits every Spatial archive member before setting the
pre-extraction flag; the native action's simpler guard alone is insufficient.

## Configuration contract

Use absolute paths for overrides. `config.local.sh` is ignored and must be
sourced explicitly; all entrypoints derive their defaults from their own clone.

| Variable | Default / use |
| --- | --- |
| `WINE_BIN` | `wine-runtime/bin/wine` if present, otherwise host Wine for diagnostics |
| `WINEPREFIX` | `<clone>/prefix`; keep stable across launches |
| `SOLIDWORKS_FULL_MEDIA_DIR` | `<clone>/full-media`, complete matching vendor media |
| `SOLIDWORKS_INSTALLER` | `$HOME/Downloads/SolidWorksSetup.exe`, optional bootstrapper |
| `SOLIDWORKS_MEDIA_DIR` | `<clone>/media`, bootstrapper extraction |
| `SOLIDWORKS_SERIAL_FILE` | `<clone>/serial.txt`, owner-only private input |
| `SOLIDWORKS_LOG_DIR` | `<clone>/logs`, never published |
| `WINETRICKS_BIN` | Host `winetricks` executable |
| `SOLIDWORKS_MSI_XML_MODE` | `builtin` only for direct MSI/repair; `prefix` is diagnostic |
| `SOLIDWORKS_WEBVIEW2_DIR` | Explicit runtime folder for optional downloader if not auto-discovered |
| `SOLIDWORKS_CDP_URL` | Bridge endpoint: localhost 9222 app wizard, 9223 downloader |
| `SOLIDWORKS_WINE_WAIT_TIMEOUT` | 180-second Wine-server idle wait |
| `SOLIDWORKS_PREREQUISITE_TIMEOUT` | 3600-second Winetricks bound |

The shared environment sets matching Wine companion binaries, `WINEARCH=win64`,
opt-in URLMon/MSI compatibility, disables menu integration/interactive debugger,
and applies WebView2 software-rendering flags. These are scoped to subprocesses,
not system registry defaults. WebView2's disabled sandbox/debugging port have
security implications: see [SECURITY.md](SECURITY.md).

## Concurrency and evidence

Core/vendor installers and repair use `.solidworks-install.lock` plus live
process checks. The lock cannot stop a person starting Wine independently.
Do not run an application during maintenance. Supervisor state is private JSON:
`running`, `stopping`, `stopped`, or `exited`, with elapsed time and stop reason.
Installer result 0 or 3010 is necessary but insufficient; require verification.
VSTA's current bootstrapper-exit check is weaker than an MSI product audit.

`--plan` and `--verify` do not request product changes, but they call Wine APIs;
Wine may start services/update its own housekeeping. Source-only tests do not
need an installed prefix. Do not mistake a CI pass for an application test.
