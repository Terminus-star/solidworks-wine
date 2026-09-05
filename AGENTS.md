# Agent instructions

## Purpose and entrypoints

This is an experimental SOLIDWORKS 2026 SP03.2/Wine 9.22 compatibility project,
not an official Linux port. Read `README.md`, `docs/INSTALL.md`,
`docs/ARCHITECTURE.md`, and `reproducibility.json` before an installation.
Read `docs/SECURITY.md` before inspecting logs, staging files, or publishing.
Historical evidence is in `docs/PROGRESS.md`; it is not a clean-install recipe.

## Protect the user's machine and license

- Never print serials, credential files, raw registry dumps, authenticated
  download URLs, activation data, or unredacted vendor logs. Use
  `python3 bin/install-controller.py log --path FILE` for serial redaction;
  even redacted logs need review for email addresses and session URLs.
- Each user supplies their own media and valid license. Do not fabricate,
  transfer, reset, or bypass activation or entitlement. Pause for personal
  details, consent to license agreements, or a vendor activation decision.
- Never commit prefixes, proprietary media/binaries, generated icons, CAD
  documents, logs, credentials, or compiled test executables. Run
  `python3 bin/audit-repository.py --staged` before commits or publication.
- Preserve existing prefixes and user edits. Do not overwrite an installed
  runtime, clear the registry, delete a prefix, or kill a process to get unstuck.
- Before any installer/repair, check the dedicated prefix's live processes.
  Never force-close an application with an unsaved document. If user activity
  appears during a test, stop GUI interaction and leave that work intact.
- Do not change global Wine, desktop hang detection, file associations, GPU
  drivers, or security policy as a silent workaround. Build locally, no sudo.
- WebView2 compatibility disables its sandbox and may expose a local debugging
  port. Do not browse unrelated/untrusted content in that environment.

## Implementation and evidence

- Keep shell scripts as thin entrypoints, Python logic in `lib/solidworks_wine`,
  Windows API probes in `native`, and Wine changes in `patches`.
- Honor environment path overrides. Never add a developer-specific home path,
  installation source path, fixed display number, or stored serial to source.
- Wine patches target exactly 9.22. MSI workarounds target exact product/action
  IDs. Other SOLIDWORKS releases need review, not widened error suppression.
- The source build recipe is not proof that a new distro works. Report patch
  application, compile, installer, file/feature audit, activation, startup,
  new document, and CAD workload results separately.
- Keep native MSXML for the web-installer environment, but use built-in MSXML
  only for the direct MSI path. Do not make that installer override a global
  app-launch default.
- `--no-splash` is only for an empty interactive launch. Do not append `/m`
  to a command containing document or macro arguments.
- Use bounded subprocesses, isolated Wine prefixes, private logs, and existing
  prefix locks. Do not install system packages or start long builds silently.

## Verification

Run `./tests/static-check.sh` and
`python3 -m unittest discover -s tests -p 'test_*.py' -v` after source changes.
Run `./bin/build-helpers.sh` after native helper changes. Patch verification
uses `python3 bin/build-wine-runtime.py --prepare-only`; a full Wine build is
expensive and must target an empty local directory. Test a source-only export
from a different path; never use the developer's existing prefix as evidence
of fresh-install portability. CI does not install or activate SOLIDWORKS.

## Handoff

Describe what changed, what was actually tested, remaining blockers, and the
exact next safe command. Never describe activation as complete from a title,
installed product record, or grace-period launch. Do not publish without the
user's chosen repository/visibility and a clean staged-content audit.
