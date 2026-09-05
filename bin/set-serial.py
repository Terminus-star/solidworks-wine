#!/usr/bin/env python3
"""Store the user's licensed serial privately, without putting it in argv."""
import argparse
import getpass
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-stdin', action='store_true', help='Read from a private pipe instead of an interactive prompt')
    parser.add_argument('--replace', action='store_true', help='Explicitly replace an existing serial file')
    args = parser.parse_args()
    destination = Path(os.environ.get('SOLIDWORKS_SERIAL_FILE', ROOT / 'serial.txt')).expanduser()
    if destination.exists() and not args.replace:
        parser.error('A serial file already exists; preserved. Use --replace only to change it.')
    if not args.from_stdin and not sys.stdin.isatty():
        parser.error('Use an interactive terminal or explicitly select --from-stdin')
    value = sys.stdin.read(128) if args.from_stdin else getpass.getpass('Your SOLIDWORKS serial (hidden): ')
    serial = re.sub(r'[\s-]+', '', value).upper()
    if not re.fullmatch(r'[0-9]{16}[A-Z0-9]{8}', serial):
        parser.error('Expected 24 characters: 16 digits followed by 8 letters/digits')
    os.umask(0o077)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=destination.parent, delete=False) as output:
        temporary = Path(output.name)
        output.write(serial + '\n')
        output.flush()
        os.fsync(output.fileno())
    temporary.chmod(0o600)
    if args.replace:
        temporary.replace(destination)
    else:
        try:
            os.link(temporary, destination)
        finally:
            temporary.unlink()
    print('Serial stored privately. It has not been activated or uploaded.')


if __name__ == '__main__':
    main()
