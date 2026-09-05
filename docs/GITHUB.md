# Publish and maintain the community repository

Git saves source history locally; GitHub hosts a remote copy. Neither should
contain the installed Wine prefix, commercial media, serial, or activation
state. Keep private, recoverable backups of your own installation separately.

## First publication from the prepared project

1. Sign in to GitHub and open [New repository](https://github.com/new).
2. Choose your account, the name `solidworks-wine`, and **Public** for community
   access. The README title is **“SOLIDWORKS 2026 on Linux: Reproducible Wine
   Compatibility Toolkit.”** Suggested description: “Experimental SOLIDWORKS
   2026 SP03.2 / Wine 9.22 toolkit: source patches, safe installers, and Linux
   reproduction docs.”
3. Leave **Add README**, **Add .gitignore**, and **Choose a license** unselected:
   these are already in this project. Click **Create repository**.
4. Connect and push the prepared local repository as shown below. Replace
   `YOUR_GITHUB_USER` with your actual account name.

This follows GitHub's [existing-project creation guidance](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository).
No paid GitHub feature is required by this project.

```bash
# In the local solidworks-wine project directory:
git status
git log -1 --oneline
python3 bin/audit-repository.py --staged
git remote -v

# Add origin only if there is not one already:
git remote add origin git@github.com:YOUR_GITHUB_USER/solidworks-wine.git
git push -u origin main
```

The preparation workflow creates a local `main` commit. If you are using a ZIP
download rather than that prepared Git repository, use the source-import
procedure below first. Do not run `git init` inside a directory already managed
by another repository. Do not force-push or overwrite an existing remote.
If `origin` already exists, check its URL and use it only if it is the intended
destination. If the remote has commits already, fetch and inspect them before
deciding how to combine histories.

SSH requires a key registered to your GitHub account. Check `ssh -T git@github.com`;
the successful greeting normally exits with status 1 because GitHub has no
interactive shell. If SSH is not configured, use GitHub's official
[SSH setup guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh).
Alternatively use HTTPS with a supported credential manager or GitHub CLI
authentication. Never put a token in a remote URL, script, command argument,
issue, or this repository.

After pushing, check the repository page and its **Actions** tab. The workflow
checks source and compiles helpers on Ubuntu runners without commercial media,
secrets, activation, or uploaded artifacts. CI passing does not mean SOLIDWORKS
works on those distributions. GitHub documents pushes
[here](https://docs.github.com/en/get-started/using-git/pushing-commits-to-a-remote-repository).

## Source import when no local Git repository exists

Run only from a reviewed source copy, after reading [SECURITY.md](SECURITY.md):

```bash
git init -b main
git add .gitignore .gitattributes AGENTS.md README.md LICENSE.md CONTRIBUTING.md \
  config.example.sh reproducibility.json assets bin docs lib licenses native patches tests .github
python3 bin/audit-repository.py --staged
git diff --cached --stat
git diff --cached --check
# Review the staged source, then:
git commit -m "Preserve SOLIDWORKS Wine compatibility toolkit and reproduction guide"
```

Never add `-f` or disable the audit to include a prefix/runtime. If Git asks for
an identity, configure your own name and, if preferred, the GitHub-provided
private/noreply email from your account settings, scoped to this repository.
Do not use another contributor's identity.

## Make the repository easy to find and contribute to

- Add topics such as `linux`, `wine`, `solidworks`, `cad`, and `compatibility`.
- Enable Issues; the included issue template asks for sanitized evidence.
- Keep README's experimental status prominent. Do not label untested distros
  supported merely because source checks pass.
- Accept documentation fixes, translations, reproducibility reports, and tests.
  No AI service or paid development tool is required to contribute.
- Preserve the MIT/LGPL/OFL boundaries and all notices. Do not distribute
  SOLIDWORKS binaries, proprietary fonts/icons, license data, or activation.
- Review Actions runs and require passing source checks for pull requests when
  practical. Keep workflows without license secrets and without privileged
  `pull_request_target` execution of contributor code.

## Save subsequent improvements

```bash
git switch -c improve-description
# Make and review your changes.
./tests/static-check.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
git add README.md docs bin lib native patches tests  # Stage only your intended changes
python3 bin/audit-repository.py --staged
git diff --cached --check
git diff --cached --stat
git commit -m "Describe the specific improvement"
git push -u origin improve-description
```

Open a pull request. Keep environment-specific overrides in ignored local
config. Rebuilding source does not require deleting the installed prefix.
For an offline source-history backup, after a clean audited commit:

```bash
mkdir -p dist
git bundle create dist/solidworks-wine-source.bundle --all
git bundle verify dist/solidworks-wine-source.bundle
```

This bundle contains Git history, not ignored installed state. Do not create a
bundle from history containing secrets and assume `.gitignore` sanitizes it.
