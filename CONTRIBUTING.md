# Contributing

Documentation corrections, translations, small source fixes, regression tests,
and honest compatibility reports are welcome. No paid tools, AI account, or
access to someone else's license is required. Treat contributors respectfully;
explain reproducible behavior, keep feedback about the work, and protect each
other's private data.

Read [README](README.md), [architecture](docs/ARCHITECTURE.md), and
[security](docs/SECURITY.md). AI assistants must also read [AGENTS.md](AGENTS.md).
Do not contribute vendor media, proprietary DLLs/fonts/icons, serials, activation
records, model files, raw logs, or authenticated URLs. Contributions to original
code use MIT; Wine-derived changes retain LGPL 2.1-or-later. Keep OFL fonts
unmodified with their license.

Use a branch and a small pull request explaining the issue, change, tests, and
remaining limitations. Add a regression test for changed behavior. Preserve
prefix isolation, credential privacy, timeout/process-group handling, argument
forwarding, and exact version/action gates. Do not broaden exception suppression
to hide a failure. Do not combine a source fix with a system-wide Wine/driver
change and claim the source fix alone resolved it.

Before submission:

```bash
./tests/static-check.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
./bin/build-helpers.sh
python3 bin/build-wine-runtime.py --prepare-only  # Required for Wine patch changes
# After staging intended source changes:
python3 bin/audit-repository.py --staged
git diff --cached --check
```

Full Wine compilation and application tests are separate, expensive checks.
Use [the validation report](docs/VALIDATION.md) to say exactly which ran. Other
distros and fresh installs are especially valuable reports. Public issues
should include only manually reviewed, sanitized summaries; redact personal
paths too. For a suspected sensitive exposure, do not repeat it publicly or
attach the affected file; contact the owner through a private channel.
