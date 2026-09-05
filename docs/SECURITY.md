# Security, credentials, and publication

Read this before inspecting logs, staging files, or publishing this repository.

## What belongs in Git

Only the maintained scripts, helper source, tests, documentation, Wine source
patches, manifest, and unmodified OFL-licensed Selawik fonts belong in Git.
`python3 bin/audit-repository.py --staged` checks the exact staged blobs, not
just the working files. Run it before every commit and push. It is a guardrail,
not a guarantee: review the staged file names and diff as well.

Never add the Wine prefix/runtime, installer media, `serial.txt`, local config,
registry exports, activation data, raw or redacted logs, session URLs, generated
SOLIDWORKS icons, screenshots containing personal details, CAD documents, or
compiled Windows binaries. Do not force-add ignored files. Git history retains
deleted secrets, so removing a credential in a later commit is insufficient.

Use `python3 bin/set-serial.py` for hidden terminal input. Each person supplies
their own valid student or other license. The serial stays in a mode-0600 local
file and goes to the MSI helper through stdin, not process arguments. Do not
put it in shell history, an issue, a chat, CI variables, or a desktop shortcut.
This project does not grant entitlement or automate license activation.

## Logs are private

Vendor actions can write serials to raw MSI logs. Controllers create private
run directories and generate serial-redacted copies, but redaction does not
remove every possible email address, hardware identifier, account/session URL,
or personal path. Even a file called `msi.log` is not automatically safe to
share. `bin/diagnose.sh` reports paths and host details; review those too.

To inspect a known vendor log locally with serial redaction:

```bash
python3 bin/install-controller.py log --path /absolute/path/to/private.log
```

Never dump whole registry files or use `rg` over `prefix/` or `logs/` with
matching lines displayed. Audit tools must report a path and reason, not the
secret they found. Keep backups of the installed prefix private and encrypted;
a GitHub source repository is not an activation or installed-system backup.

## Runtime isolation is not a security sandbox

Wine applications can access host files through their drive mappings. Only run
trusted, legally obtained vendor media. Use an ordinary user, never root. The
WebView2 workaround disables browser sandbox/GPU restrictions and enables a
debugging port (9222, or 9223 for the downloader). Do not expose these ports,
forward them over the network, or load unrelated/untrusted content. The tested
WebView2 119 runtime is old; it is recorded as evidence, not a security
recommendation. Newer runtimes require independent compatibility testing.

MSI watchdogs may stop this dedicated prefix's Wine server after a timed-out
install. Close SOLIDWORKS and all work in that prefix before installation or
repair. Locks coordinate these scripts, not arbitrary Windows programs.

## Publishing checklist

1. Confirm the destination account, repository name, and visibility.
2. Run the tests and `git status --short --ignored` (filenames only).
3. Stage only the documented source directories, never `git add -f`.
4. Run `python3 bin/audit-repository.py --staged` and review the staged diff.
5. Confirm licensing in `LICENSE.md` and third-party notices.
6. Commit, inspect the committed tree, and push over an authenticated channel.

If a credential was already published, treat it as exposed. Contact the
credential issuer about replacement, restrict access, and coordinate history
cleanup with collaborators. Do not paste the credential into an issue.
