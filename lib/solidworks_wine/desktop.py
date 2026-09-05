"""Generate a freedesktop launcher without assuming a username or clone path."""
from pathlib import Path


def value(text):
    return str(text).replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')


def exec_argument(text):
    # Desktop Exec quoting is NOT shell quoting. Percent is a field-code
    # escape; backslash passes through both key-value and Exec parsing.
    text = str(text).replace('%', '%%').replace('\\', '\\\\')
    for character in ('"', '`', '$'):
        text = text.replace(character, '\\' + character)
    return value('"' + text + '"')


def render(root: Path, prefix: Path, wine: Path):
    launcher = root / 'bin/run-solidworks.sh'
    icon = root / 'assets/solidworks.png'
    command = ['/usr/bin/env', 'WINEPREFIX=' + str(prefix), 'WINE_BIN=' + str(wine),
               str(launcher), '--no-splash']
    return '\n'.join([
        '[Desktop Entry]', 'Type=Application', 'Version=1.0',
        'Name=SOLIDWORKS 2026 (Wine)',
        'Comment=Launch SOLIDWORKS with its private Wine runtime and compatibility settings',
        'Exec=' + ' '.join(exec_argument(item) for item in command),
        'TryExec=' + value(launcher), 'Path=' + value(root),
        'Icon=' + value(icon if icon.is_file() else 'applications-engineering'),
        'Terminal=false', 'StartupNotify=true', 'Categories=Graphics;Engineering;',
        'X-SolidworksWine-Launcher=true', '',
    ])
