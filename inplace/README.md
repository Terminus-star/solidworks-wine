# In-place SOLIDWORKS: how it works

Install steps are in the [top-level README](../README.md#install-run-your-existing-windows-solidworks).
This page explains what each piece does, what to do when something goes wrong,
and the known issues.

Tested with SOLIDWORKS 2022 SP02 (Education, network licence) on CachyOS,
KDE Plasma 6.8, CachyOS Wine 10.0, on an ASUS ROG Flow Z13. Other versions and
setups are untested.

## The idea

Instead of installing SOLIDWORKS into Wine, the Wine prefix borrows the copy
that is already installed on your Windows partition:

1. **Files** stay on the Windows partition. `sw-link.sh` symlinks the install
   folders into the prefix at the same `C:\` paths Windows uses, so every path
   in SOLIDWORKS' registry entries stays valid, and adds a `W:` drive for the
   whole partition.
2. **Registry**: SOLIDWORKS' settings, COM registrations and file associations
   live in the Windows registry. `sw-reg-export.sh` reads them from the
   offline hive files (read-only) and `sw-reg-import.sh` imports them.
3. **Runtimes** (VC++, .NET 4.8, MSXML) come from winetricks
   (`bin/setup-prefix.sh`), because Windows' own system DLLs can't be shared.
4. **Licence**: a network licence is just a `port@server` address and is
   exported automatically. A standalone activation is tied to the machine and
   must be redone inside Wine.

## The scripts

| Script | What it does |
|---|---|
| `sw-link.sh` | Symlinks the install folders and `W:` into the prefix. Re-run with `WIN_ROOT=…` to point elsewhere (e.g. the overlay). |
| `sw-reg-export.sh` | Exports vendor keys, per-user settings and the COM entries SOLIDWORKS registered (CLSIDs, TypeLibs, Interfaces, ProgIDs, file extensions, AppIDs) into `./sw-registry/`. Writes UTF-16 copies for import. |
| `sw-reg-import.sh` | Imports those files and checks that a string came back intact. |
| `solidworks-2022` | The launcher. Pins startup to one CPU, then releases all cores once the main window appears (see the deadlock below). |
| `install-shortcut.sh` | Installs the launcher, the app-menu entry, and an icon extracted from your own `SLDWORKS.exe`. |
| `kwinrules-solidworks.kwinrule` | KWin rules for KDE: see "Focus" below. Import in System Settings → Window Rules. |
| `build-wine-portal.sh` | Optional: CachyOS Wine 10 + MR !10060 for native file dialogs. |
| `sw-overlay.sh` | Optional: a writable overlay over a read-only Windows partition, for a cautious first trial. |
| `launch-test.sh` | Measures the startup deadlock (alternating pinned / unpinned launches). |

`sw-registry/` contains your licence server address and personal settings —
it is git-ignored; never publish it.

## Safety rules

- **Never boot Windows (VM or native) while the partition is mounted on
  Linux.** Two systems writing the same NTFS volume corrupts it. Turn off
  Windows Fast Startup so the volume isn't left "dirty".
- SOLIDWORKS edits your real files through `W:\…`. Keep backups.
- If a Windows VM unmounts the partition with a lazy/forced unmount, take the
  overlay down first (`sudo inplace/sw-overlay.sh down`).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| "Couldn't find the license file" | Network licence: check the server is reachable (`nc -z <server> <port>`; campus network or VPN). Standalone: re-activate inside Wine. |
| Freezes at startup with no window, 0 % CPU | The loader-lock deadlock. Use the launcher (it pins startup); never start `SLDWORKS.exe` directly. |
| Part opens `[Read-only]` | It was opened through a read-only path (e.g. `Z:\mnt\windows\…` while mounted read-only). Mount read-write and open via `W:\…`. |
| Everything is tiny / blurry | Set the Wine DPI (`LogPixels`, 96 × your scale). On KDE with "Legacy applications: apply scaling themselves" it stays sharp. |
| Imported registry values show one character (`S`, `{`) | The `.reg` files were imported without the UTF-16 byte-order mark. Re-run `sw-reg-export.sh` and `sw-reg-import.sh`. |
| Can't attach a debugger | Attaching `winedbg` kills SOLIDWORKS. Use trace channels (`WINEDEBUG=+loaddll,+module,+seh solidworks-2022`). |

Launcher logs: `~/.local/state/solidworks-2022/`.

## Known issues

**Startup deadlock (worked around).** Wine holds one loader lock for a whole
DLL load and for `GetProcAddress`/`GetModuleHandle`; Windows only holds it for
`DllMain`. SOLIDWORKS loads ~180 DLLs on a background thread while other
threads take MFC's or FlexNet's locks, and the two can deadlock. Unpinned,
5/5 traced launches deadlocked; pinned to one CPU during startup, 0/5. The real
fix would be in Wine's loader (`dlls/ntdll/loader.c`).

**Focus (KDE rules).** Under Wine, SOLIDWORKS' main window became fullscreen
and focus jumped between windows:
- SOLIDWORKS creates an invisible 0×0 top-level window per document (likely a
  taskbar proxy). Under Wine it's a real 1×1 window.
- The FeatureManager "Filter Quick Hits" list is an unowned popup. When it
  closes, Wine activates the next window in the stack — the invisible proxy —
  and SOLIDWORKS then moves focus into the 3D view, mid-typing.

The rules keep the main window maximised (not fullscreen), stop the proxy and
the filter list from taking focus, and give the splash screen a taskbar entry.
Remaining: the taskbar entry can flash orange ("demands attention") because
KWin declines to activate some small popups.

**Wine 11.20.** The X11 driver gives a black 3D viewport (Wine 11's new OpenGL
code doesn't handle SOLIDWORKS' OpenGL 4 / robust-access context request). The
Wayland driver shows windows transparent (likely
`wayland_surface_ensure_contents`, see Wine MR !11220). Stay on Wine 10.

**Wine 9.22** (the upstream recipe) doesn't start when built with binutils
≥ 2.47: `.idata` becomes read-only and the delay-load code faults.

**Native file dialogs** (`build-wine-portal.sh`): SOLIDWORKS customises its
Open/Save dialog, so `FileDialogPortal=auto` falls back to Wine's picker; use
`always` (SOLIDWORKS' extra panes are then missing).

**Not covered:** VBA/VSTA (macros), COM automation from other programs (the
registry uses Windows 8.3 short paths that Wine generates differently).
