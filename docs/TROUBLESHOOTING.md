# Troubleshooting

Read [security](SECURITY.md) before opening logs. Close all work before repair.
Do not delete the prefix, reset activation, or repeatedly rerun setup to fix a
single failed step. A watchdog timeout preserves private evidence for diagnosis.

## Startup splash is unresponsive, but the application works

Use `./bin/run-solidworks.sh --no-splash` or the generated desktop entry.
This uses `/m` without a macro filename, an observed undocumented behavior for
this release. It is only added to an empty launch. Opening a document or using
explicit macro arguments preserves normal semantics. Startup initialization
still occurs. To restore the splash, run without `--no-splash`; no desktop-wide
hang-detection preference has been changed.

## Segoe UI unavailable

Close SOLIDWORKS and run `./bin/configure-fonts.sh`, then restart. Build helpers
first if `font-probe.exe` is missing. The fix uses unmodified OFL Selawik fonts
and a Wine-only missing-family alias; it is not proprietary Segoe UI. Documents,
templates, and warning preferences are unchanged. Review typography before
using generated drawings. Do not download random proprietary font copies.

## Login Manager missing or registration type keeps returning

First confirm that all launches use the same `WINEPREFIX` and private runtime.
Generate the shortcut with `./bin/install-desktop-shortcut.sh`. Close the app,
then run `./bin/repair-login-manager.sh` if its prerequisite warning returns.
Complete official activation with your own license. Repeated prompts may be
an entitlement/activation problem rather than a setting; consult your school
or vendor. Never copy another user's registration or suppress license checks.

## Black Installation Manager

The preferred core install uses complete media and `install-solidworks-direct.sh`.
The web installer can render internally but fail to paint its native window.
A black body alone does not prove a hang. The optional bridge observes that
page; it is not a native-window rendering fix.

If complete media is unavailable, prefer an authorized download on supported
Windows. The experimental Linux downloader requires its own prefix, native
MSXML, .NET, VC++, and WebView2. Its tested WebView2 version was 119.0.2151.97,
which is old and should not be treated as a secure general browser. Newer
vendor runtimes require testing. Do not fetch old binaries from random mirrors.

Optional setup from the clone, with the private Wine runtime already built:

```bash
WINEPREFIX="$PWD/download-prefix" ./bin/setup-prefix.sh
WINEPREFIX="$PWD/download-prefix" ./bin/install-solidworks.sh --extract-only
python3 -m venv .venv
.venv/bin/pip install websocket-client==1.8.0
```

Install the WebView2 runtime provided by your authorized matching media into
that download prefix using its normal vendor installer. This may download a
newer runtime and is not independently validated. Set `SOLIDWORKS_WEBVIEW2_DIR`
to the absolute directory containing `msedgewebview2.exe` if auto-discovery
cannot choose exactly one runtime. Do not source/copy the application prefix's
registry wholesale. Build helpers before starting the downloader.

```bash
./bin/download-media.sh
```

While it runs, a second terminal can inspect the local page:

```bash
SOLIDWORKS_CDP_URL=http://127.0.0.1:9223 .venv/bin/python bin/installer-bridge.py status
SOLIDWORKS_CDP_URL=http://127.0.0.1:9223 .venv/bin/python bin/installer-bridge.py capture /tmp/solidworks-page.png
```

Screenshots/page data can contain credentials. Keep them private. The bridge
has `--help` and accepts serial input privately through stdin. Do not put a
serial in command arguments. Wizard interactions and acceptance of terms remain
the user's responsibility. Do not expose the debugging port or keep unrelated
browser content open. The downloader is bounded and isolated from the main
prefix; do not restart an active download because a bridge call times out.

## MSI success without a working application

Use `./bin/install-solidworks-direct.sh --verify`. A registered product without
the required core files and selected features is a failure. Missing Toolbox
archives must be downloaded from authorized sources; `--plan` lists them.
The scoped MSI exception workaround requires independent runtime checks.

`bin/download-toolbox.py` / `bin/extract-toolbox.py` are recovery utilities for
the vendor's metadata and authenticated download flow, not public media mirrors.
Read `--help` before use; never publish a captured vendor URL or download log.

## Compiler errors or incompatible Wine

Read the failing `build/repro-wine/step-N.log` locally. A 32-bit configure failure
usually warrants checking i386 development libraries and multilib, not disabling
TLS/graphics checks. The runtime builder refuses a nonempty destination. Use a
new work/runtime directory for another recipe; keep the original working one.
Do not apply these patches to another Wine version without reviewing the diffs.

## Graphics failures or slow viewport

For a one-off diagnostic, try `./bin/run-solidworks.sh --software-rendering`.
CPU rendering is slower and not a performance fix. Inspect matching host/32-bit
graphics drivers; don't change system GPU/desktop settings automatically.
`./bin/diagnose.sh` writes local host/path details requiring privacy review.

## Shortcut does not launch

Use an absolute private `WINE_BIN`, confirm the prefix exists, and regenerate
the shortcut after a move. Wine build paths may also require a rebuild. Trust
the desktop file using the desktop UI if required. Some desktops do not display
desktop icons; the shell launcher remains available. Do not use an old `.lnk`
that points at another Wine prefix.
