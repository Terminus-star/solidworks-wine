#!/usr/bin/env python3
"""Install an executable desktop entry generated for the current clone."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from solidworks_wine.desktop import render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desktop-dir', type=Path)
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    desktop = args.desktop_dir
    if desktop is None and shutil.which('xdg-user-dir'):
        result = subprocess.run(['xdg-user-dir', 'DESKTOP'], text=True, capture_output=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip():
            desktop = Path(result.stdout.strip())
    if desktop is None:
        parser.error('Desktop directory not discoverable; specify --desktop-dir explicitly')
    desktop = desktop.expanduser().resolve()
    if desktop == Path.home() or desktop == Path('/'):
        parser.error('Desktop is disabled or points to a broad directory; specify --desktop-dir')
    wine = Path(os.environ['WINE_BIN']).resolve()
    prefix = Path(os.environ['WINEPREFIX']).expanduser().resolve()
    if not os.access(wine, os.X_OK) or not (prefix / 'system.reg').is_file():
        parser.error('Configure the private runtime and prefix before creating the shortcut')
    content = render(ROOT, prefix, wine)
    desktop.mkdir(parents=True, exist_ok=True)
    target = desktop / 'SOLIDWORKS.desktop'
    if target.exists() or target.is_symlink():
        if target.is_symlink():
            parser.error('Existing shortcut is a symlink; preserved. Choose another directory.')
        if target.read_text() != content:
            if not args.replace:
                parser.error('A different shortcut exists; preserved. Use --replace to back it up and replace it.')
            backups = ROOT / 'logs/desktop-backups'
            backups.mkdir(parents=True, exist_ok=True)
            folder = Path(tempfile.mkdtemp(prefix='shortcut-', dir=backups))
            shutil.copy2(target, folder / target.name)
            print('Previous shortcut backed up:', folder / target.name)
    with tempfile.NamedTemporaryFile(mode='w', dir=desktop, suffix='.desktop', delete=False) as output:
        temporary = Path(output.name)
        output.write(content)
    if shutil.which('desktop-file-validate'):
        subprocess.run(['desktop-file-validate', str(temporary)], check=True, timeout=5)
    temporary.chmod(0o755)
    temporary.replace(target)
    trusted = False
    if shutil.which('gio'):
        result = subprocess.run(['gio', 'set', str(target), 'metadata::trusted', 'true'],
                                capture_output=True, timeout=5)
        trusted = result.returncode == 0
    print('Installed:', target)
    if not trusted:
        print('If required by your desktop, right-click and choose Allow Launching / Trust.')


if __name__ == '__main__':
    main()
