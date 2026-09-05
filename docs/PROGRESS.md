# Installation progress and evidence

This is a historical notebook. Use [INSTALL.md](INSTALL.md) for the current
reproduction procedure and [VALIDATION.md](VALIDATION.md) for evidence limits.
Private log/screenshot paths below are intentionally not distributed.

## 2026-09-04 — Community source packaging

Preserved the Wine patches, maintained helpers, font workaround, no-splash
launcher, and investigation source. Added MIT licensing for original work,
upstream LGPL/OFL notices, portable local configuration, a pinned Wine source
build recipe, explicit vendor-prerequisite runner, detailed human/agent guides,
source-only CI, and staged-content publication checks. Thirty-three regression
tests and an independent source-only export passed. The new full clean runtime
build and vendor installation sequence still need end-to-end validation.
No installed prefix, activation state, commercial media, or proprietary icon
belongs in Git. GitHub creation/push instructions are in [GITHUB.md](GITHUB.md).

The older note below about two Spatial endpoint checks refers to the shell/native
guard. The current Python install controller additionally checks every archive
member's presence and size before enabling the extraction skip. Dated activation
and test-count statements below describe those historical runs, not current
entitlement or a new cross-distro validation claim.

Final outcome on September 4: the core application and Login Manager are
installed, the independent installation audit passes, and SOLIDWORKS opened a
new Part1 document and exited normally. Twelve regression tests pass. Permanent
activation and production-level CAD validation remain separate follow-up work.

## 2026-09-04 — Startup-only splash warning

The user confirmed that Cinnamon's `splash is not responding` warning occurs
only during startup, not while using the workspace. The desktop's existing
`org.cinnamon.muffin check-alive-timeout` is 5000 ms. Wine 9.22 advertises
`_NET_WM_PING` for its X11 windows and answers it from its event processing.
The ordinary launch did recover without force-quitting: during the first
30 seconds it continued consuming CPU and loading memory, with the main window
appearing around 14 seconds while the splash remained. Thus the observed
warning is consistent with a busy startup window missing the desktop timeout,
not evidence of a permanently hung application.

Tested `SLDWORKS.exe /m` with no macro filename in the existing patched runtime.
The splash was absent throughout 0–40 seconds of observation; the normal full
2560x1400 interactive workspace appeared around 14 seconds. Native window
inspection then showed the welcome page with New Part/Assembly/Drawing controls,
no splash and no macro-error dialog. This was not batch or safe mode, and no
license, add-in, rendering, or desktop-wide hang-detection settings were changed.
The test application is left open for the user.

`/m` is ordinarily the startup macro option; using it without a filename to
avoid the splash is tested behavior in this version, not a documented general
`/nosplash` interface. The launcher exposes it as `--no-splash`, used by both
copies of `SOLIDWORKS.desktop`. It only adds `/m` on an otherwise empty launch;
document/macro arguments retain normal startup so they cannot accidentally be
interpreted as a startup macro. Remove the option to restore the old behavior.
This removes the problematic splash, not the underlying initialization work.

Logs: `logs/solidworks-20260904-215013.log` (ordinary startup),
`logs/solidworks-20260904-215403.log` (no-splash test). The ordinary empty test
session was closed normally before starting the second. No models were opened,
saved, discarded, or changed during these tests. Desktop validation and shell
checks pass; the regression suite now also checks argument forwarding for
normal, no-splash, document, and explicit-macro launches.

## 2026-09-04 — Missing Segoe UI in standard templates

The template font warning was reproduced as a genuine missing family:
`native/font-probe.c` found zero `Segoe UI` matches through 64-bit Windows GDI
font enumeration before the change. No local Segoe UI installation was found.

Installed the five unmodified TrueType weights from Microsoft's official
Selawik 1.01 release, retaining its SIL Open Font License. Only this prefix's
Windows font directory and registry were changed. The family replacement
`HKCU\Software\Wine\Fonts\Replacements`, `Segoe UI` = `Selawik`, makes Wine
enumerate the alias; simply allowing an implicit rendering fallback would not
fix a missing-family check. Wine ignores the alias if genuine Segoe UI is later
installed. Selawik is a substitute with different kerning/hinting, not Segoe UI.

After installation the probe reported four matches in all-family enumeration,
eight matches when requesting the family, and selected face `Segoe UI`.
`bin/configure-fonts.sh` makes the offline, checksummed setup repeatable and
refuses to overwrite different font binaries. Previous font registrations are
in `logs/fonts-bTPSE6MI/`. No documents/templates were saved or changed, no font
files were renamed internally, and the warning checkbox was not suppressed.
Shell static checks and all 12 Python regression tests pass.

A fresh application launch opened the existing `Part.PRTDOT` template into
the main workspace without the missing-font dialog. Its title was
`SOLIDWORKS Design Premium for Students 2026 SP3.2 - Academic Use Only - [Part.PRTDOT]`.
No activation interaction was needed during this font test. The template was
not edited or saved. Run log: `logs/solidworks-20260904-214548.log`.
The font probe also passed for `Selawik` and correctly returned failure for a
deliberately nonexistent family, ruling out an always-successful probe.
During handoff, a new unsaved `Draw1 - Sheet1` appeared in the application.
After one normal close request, the application remained open. No discard or
save action was taken; further GUI interaction was stopped to preserve that
user work. The font-test application is therefore left running.

## 2026-09-04 — Recover the missing core application

Current target: SOLIDWORKS 2026 SP03.2 (MSI product version 34.132.0003),
product code `{6172DDB3-98E6-46E1-A0C1-DB8FD05063EF}`.

The previous attempt is classified as progress: it produced an MSI log and
installed Task Scheduler, which provide evidence for the next correction.
The current-state check found no running installer. No restart was based on a
stale lock or observation timeout.

### Finding

`logs/solidworks-direct-20260902-214815.log` ends with successful MSI actions,
but its ADDLOCAL list omits `SolidWorks`. Direct MSI API inspection confirmed
product state 5 (registered), Task Scheduler state 3 (local), and states 2
(absent) for `SolidWorks`, `ProgramFiles`, `i386_SWFiles`, and `FeatureWorks`.
There was no SLDWORKS.exe. Successful registration of the product alone did
not mean the application was installed.

### Changes

- Added `native/msi-tool.c` to inspect the actual MSI tables, install through
  the Windows Installer API, and query installed product/feature state.
- Added separate Python modules for credentials, MSI selection, process
  supervision, and verification. The existing shell launcher prepares the
  project Wine environment and payloads before calling the controller.
- The selection includes `SolidWorks` and explicitly expands default child
  features from the vendor Feature table, preserving the earlier requested
  Task Scheduler, examples, help, Utilities, FeatureWorks, and Treehouse roots.
  For this package the plan selects 141 features. OFFICEOPTION remains 0;
  this installs the core/default product configuration, and does not claim
  Premium add-on coverage or activation.
- Replaced hard-coded Wine short directory names with quoted Windows paths.
- The supplied serial is validated, protected with mode 0600, and sent through
  stdin to the native helper. It is not included in process arguments. The MSI
  hidden-property setting is enabled, but vendor custom actions can still log
  serials; raw logs live in a private directory and separate redacted logs are
  produced for review. `install-controller.py log --path ...` safely reads old
  logs too.
- Added prefix locking, live process checks, reduced scheduling priority,
  four-CPU affinity for the new installer process tree, a wall timeout, an
  inactivity timeout, and a 256 MiB combined output limit. A timeout preserves
  evidence and stops the dedicated prefix. Existing Wine server processes do
  not necessarily inherit the new affinity.
- Verification requires successful MSI status, locally installed selected
  features, and real core files. Runtime and activation are separate checks.

First corrected run: `logs/install-20260904-172633/` exited with MSI 1603 after
152 seconds. Core files were copied, but native MSXML produced an empty
registration document and failed to load the Toolbox XML resource. MSI rolled
back. The verifier correctly rejected the attempt.

Second run: `logs/install-20260904-172953/` used built-in `msxml3,msxml6` for
the offline MSI. Type-library, DLL and .NET registration completed; the Toolbox
XML resource loaded and `C:\\SWData\\ToolboxStandards.xml` was written. This
direct-install-only XML override is now the default. The run then failed at
`SldToolboxUpdater` because the downloaded media has no `toolbox/` directory.
It exited with MSI 1603 after 246 seconds and rolled back. The previously
described "complete media" was only complete for the selected core downloads.

The saved vendor GetSourceInfo catalog identifies 19 missing Toolbox archive
packages. The graphical manager was started with a ten-minute bound to obtain
the missing media through its normal download workflow. Its CDP connection
was initially unreachable because an older Wine server still held the IPv4
9222 socket. The new WebView2 instance was reachable on IPv6 localhost; the
bridge now tries both addresses and bypasses HTTP proxy settings for this local
connection. It can read the actual page and submit the supplied serial.

Seven regression checks pass, including omitted-core rejection, serial redaction,
duplicate-controller rejection, a real hung-process watchdog stop, and refusal
to accept an exit code without core files. Shell static checks pass. New log
redaction also handles UTF-16 logs, 16-character serial prefixes, and encoded
serial query parameters. Current installation remains unverified.

### Download isolation and prerequisite checks

The manager in the application prefix stopped progressing at client detection
after serial validation. It was stopped through that prefix's Wine server.
`download-prefix/` was initialized separately, with native VC++/MSXML and the
existing WebView2 runtime. The new manager successfully opened its wizard on
port 9223, avoiding the earlier stale debugging-port socket.

The isolated manager then returned a COM error during entitlement checking.
The new `com-probe.exe` proved that versioned `Msxml2.XMLHTTP.3.0` and `.6.0`
worked, while `Msxml2.XMLHTTP` failed with 0x80040152. Its registry alias still
pointed to Wine's MSXML2 class after Winetricks installed native MSXML3.
`configure-download-prefix.sh` maps the 32-bit alias to the installed MSXML3
class and checks COM activation before starting the manager. This is a local
prerequisite correction, not an entitlement override.

.NET 4.0 completed in the download prefix. A service shutdown intended to
release a Winetricks wineserver wait overlapped the next .NET 4.8 launch,
interrupting it. The interruption is recorded in
`logs/download-prefix-dotnet48.log`. The .NET 4.8 prerequisite was restarted
directly from the cached Microsoft installer, under a ten-minute bound, with
output in `logs/download-prefix-dotnet48-retry.log`. The retry returned exit code
0 and the v4 Full registry Release value was verified as 528049 (0x80eb1).
The Edge updater services in this isolated prefix were disabled to prevent
background service launches from blocking installer shutdown.

The direct installation now refuses missing Toolbox media before payload
preparation. Payload preparation moved inside the controller's prefix lock.
The Spatial IOP audit now checks every archive member's existence and size;
the current extracted payload passed with zero missing or wrong-sized files.

### Black-window evidence and authorized missing-media recovery

The isolated manager passed client detection and reached its full-download
summary at 17:57:14. The black native window hid a functioning WebView2 page;
a CDP framebuffer capture at `/tmp/solidworks-installer-current.png` showed the
correct summary. Existing software-rendering flags do not fix presentation on
this host. The bridge provides inspection/control despite that display failure.
Connection interruptions are now reported as bridge errors rather than raw
WebSocket tracebacks; observation polling closes its sockets.

Future-service-pack background downloads were unchecked before starting the
normal vendor download workflow. It generated fresh authenticated download
requests. The graphical download was stopped in its dedicated prefix to avoid
fetching 12 GB of unrelated full-media content. `download-toolbox.py` reuses the
vendor-generated session for the 19 missing Toolbox packages (377,065,096 bytes)
from the supplied catalog, with HTTPS, vendor-only redirects, two connections,
size/time limits, private files, and an exclusive downloader lock. No licensing
or entitlement checks were disabled. Expired requests require refreshing the
normal wizard session.

An initial standard CRC32 validation refused to stage these files, but
investigation showed that the vendor's `CheckSum32` is not standard CRC32.
The supplied manager's file-checksum loop (sldIM.exe VA 0x00a8e3f0–0x00a8e40f)
uses polynomial 0xedb88320, seed 0xffffffff, and complements after **each byte**.
`native/media-checksum.c` independently implements that recurrence. All 19
downloaded executables matched their catalogued sizes and vendor checksums.
Previously downloaded complete `.part` files were validated and reused.

`extract-toolbox.py` rechecks the complete package set, permits only each
expected nested Toolbox ZIP, validates outer and inner ZIP integrity, preserves
different existing files, and records SHA-256 payload hashes. All 19 archives
were successfully staged into `full-media/toolbox/`. Download evidence and the
extraction report are under `logs/toolbox-packages-20260904/`.

Recovery commands (paths are local vendor catalogs/logs; keep session logs private):

```bash
python3 bin/download-toolbox.py --catalog PATH_TO_GetSourceInfo.xml \
  --session-log PATH_TO_FRESH_sldIMLog.txt --destination logs/toolbox-packages
python3 bin/extract-toolbox.py --catalog PATH_TO_GetSourceInfo.xml \
  --packages logs/toolbox-packages --media full-media
```

Build the checksum helper with `bin/build-helpers.sh` before downloads and before
starting an installer. The normal wizard must first obtain a fresh authorized
session; the recovery command cannot mint or renew vendor credentials. Ten
regression tests and the shell static checks pass after these changes.

### Core MSI success and separate startup failure

`logs/install-20260904-181055/` completed in 316 seconds with MSI result 0,
installed product state 5, and all three checked core files present. The Toolbox
updater finished successfully after roughly three minutes; it was not hung.
The strict verifier still returns false because six features report SOURCE
instead of LOCAL. A 2,003-component audit found that the suspicious paths are
registry keypaths such as `02:\\Software\\...`, which Wine's feature-state
query classifies as source merely because they start with two digits. The
audit also records conditionally excluded components and a managed assembly;
this is not yet a blanket waiver of feature verification.

The first startup reached the genuine SOLIDWORKS activation wizard. Its offered
30-day grace period was selected for the smoke test; permanent activation has
not been performed. Wine Gecko was installed through its normal prerequisite
dialog, and the first-run license agreement was accepted. The application
then crashed before reaching a usable workspace. Its private minidump and
performance log identify an access violation reading address 8 in
`COMCTL32.dll+0x2a438`, called from `sldimporttabu`. Debug symbols resolve this
to Wine 9.22 `HEADER_Layout`, which dereferences a null layout pointer. Missing
OpenXR-library warnings also occurred, but they are not the recorded crash site.

The crash evidence is under the prefix's user-local
`SolidWorks/CXPD/20260904181757_34.3.2.0003/`, and the launch console is
`logs/solidworks-20260904-181756.log`. Installation success is not being presented
as proof of a working application. A narrow common-control guard is being
prepared for the project-private runtime; no system Wine DLL has been changed.

### Common-control fix and verification refinements

The guard was compiled from the existing Wine 9.22 source archive in the
project's `build/wine64-source/` and `build/wine64-comctl/` directories. Only
`dlls/comctl32/x86_64-windows/comctl32.dll` was built and staged into the private
runtime. Its original system-library symlink is preserved as
`comctl32.dll.original-link`. `patches/wine-comctl32-header-layout.patch` records
the source change. `native/header-layout-test.c` verifies a normal layout call
and rejection of null layout, rectangle, and output-position pointers; all four
cases passed. The system DLL remains unchanged.

With that fix, SOLIDWORKS reached its main workspace instead of the previous
header-control crash. It then displayed a Login Manager prerequisite warning
and exited after acknowledgment, so the new-part smoke test is not yet passed.
`repair-login-manager.sh` repairs the existing bundled prerequisite with builtin
MSXML and the same private logging, prefix lock, and watchdog used for the core
installer. Repair evidence is in `logs/login-manager-20260904-183554/`.

The refined verifier passed in `logs/verification-20260904-current.json`:
all selected features are installed, the six SOURCE states are explained by
registry-backed keypaths, and no actual source-file or missing local-keypath
exception was found in those features. The report retains the raw states and
the audit details. Actual disk-source prefixes are explicitly rejected; this is
not a blanket acceptance of SOURCE. Managed-assembly identities and inactive
component paths are distinguished from disk-source paths.

Read-only helper calls now capture output in temporary files rather than pipes.
A Wine service inherited a verification helper's pipe, causing a false timeout
after that helper had already exited; the new method waits on the helper process
itself. Verification remains protected against a concurrent installation but
can now run while the application is open.

The Login Manager repair completed in four seconds with MSI result 0 and product
state 5. Its actual 64-bit RegAsm `/codebase` registration returned 0; this run
did not need to ignore a registration crash. Twelve Python regression tests
and the shell static checks pass, including a test where a child inherits a
helper's output handle and the reader must not wait for that child's lifetime.

To rebuild the private common-control DLL from the preserved source/build trees:

```bash
nice -n 10 make -C build/wine64-comctl -j4 dlls/comctl32/x86_64-windows/comctl32.dll
```

The build was configured with `--enable-win64 --without-x --without-wayland
--without-opengl`; these settings apply only to this isolated DLL build, not to
the installed runtime's graphics drivers. Replacing runtime DLLs requires
stopping applications using that prefix first. The recorded patch and header
layout regression test must accompany future Wine upgrades.

### Final installation and new-part smoke test

The repaired prerequisite removed the Login Manager warning. A fresh launch
opened the main workspace and created a new `Part1` document. Its window title
was `SOLIDWORKS Design Premium for Students 2026 SP3.2 - Academic Use Only - Part1`.
The viewport, default reference planes, origin, and modeling toolbars were
visible. The successful launch log is `logs/solidworks-20260904-184152.log`.
The final independent install audit in `logs/verification-20260904-final.json`
passes for the product, 141 selected features, and required core files.

The earlier four-minute smoke-test limit expired during first-use template and
font prompts, not during an installer operation. The final run used a ten-minute
bound and completed the new-part check. Missing Segoe UI was handled with the
application's temporary font substitution; original font choices were not
permanently replaced. Permanent activation is still pending; the vendor's
offered 30-day grace period was used. These checks do not establish complete
add-in compatibility, advanced graphics support, or production CAD reliability.

The direct-install launcher now follows a successful core install with the
separate Login Manager repair, after the core prefix lock is released. Planning
and verification stay read-only. This composes the two proven installation
steps so subsequent attempts do not omit that runtime prerequisite.

The clean successful-workspace screenshot is
`logs/solidworks-part1-verified.png`. The final smoke test used an empty new part;
no existing user model was opened or modified.
The test document and application were closed normally; the final launcher
returned exit code 0, rather than timing out. No active installer or main
SOLIDWORKS application was left running. Some optional-library and message-file
warnings remain in the launch log; only installation, startup, and an empty
new-part workflow have been validated.

### Earlier fixes preserved from the current worktree

These source changes predate this continuation. The snapshots document the
actual implementation; their full effects have not been independently proven.

| Component | Observed purpose | Project patch |
| --- | --- | --- |
| Windows UI | Supplies IAgileObject and text scale 1.0 for WebView2 | `patches/wine-windows-ui-text-scale.patch` |
| URLMon | Makes native MSXML receive readable synchronous streams | `patches/wine-urlmon-msxml-stream.patch` |
| WinINet | Preserves prefetched HTTP bytes on stream rewinds | `patches/wine-wininet-response-seek.patch` |
| MSI | Handles exact registration-action crashes and replaces dead action servers; skips Spatial IOP shell extraction only when pre-extracted files exist | `patches/wine-msi-solidworks-actions.patch` |

The MSI workaround accepts certain registration crashes. An installer success
under that workaround requires runtime verification; it is not proof that all
registration completed. The Spatial IOP check currently checks two endpoints,
not every archived file. Scheduler language resources are staged from the
supplied cabinet before their registration action.

### References

The vendor's [2026 installation guide, pages 41–44](https://files.solidworks.com/Supportfiles/SW_Installation_Guide/2026/English/install_guide.pdf)
documents command-line MSI installation, `ADDLOCAL=SolidWorks`, install paths,
serial properties, and OFFICEOPTION. The current feature plan is obtained from
the supplied MSI itself, not a guessed feature list.
