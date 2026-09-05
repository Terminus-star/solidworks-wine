#!/usr/bin/env python3
"""Audit the complete Git index before committing or publishing source."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from solidworks_wine.repository import audit_blob


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, timeout=30)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staged', action='store_true', help='Audit all staged blobs (also the default)')
    parser.parse_args()
    records = []
    for entry in git('ls-files', '--stage', '-z').split(b'\0'):
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, oid, stage = metadata.decode('ascii').split()
        records.append((os.fsdecode(raw_name), mode, oid, stage))
    if not records:
        raise ValueError('Git index is empty; explicitly stage the intended source files first')
    serial_path = Path(os.environ.get('SOLIDWORKS_SERIAL_FILE', ROOT / 'serial.txt'))
    serial = serial_path.read_text() if serial_path.is_file() else ''
    fonts = {}
    for name, mode, oid, stage in records:
        if name == 'assets/fonts/SHA256SUMS' and mode == '100644' and stage == '0':
            for line in git('cat-file', 'blob', oid).decode().splitlines():
                checksum, filename = line.split(maxsplit=1)
                fonts[filename.lstrip('*')] = checksum
    failures = []
    total = 0
    for name, mode, oid, stage in records:
        if stage != '0':
            failures.append({'path': name, 'reasons': ['unmerged index entry']})
            continue
        if mode not in ('100644', '100755'):
            failures.append({'path': name, 'reasons': ['symlink or non-regular source entry']})
            continue
        size = int(git('cat-file', '-s', oid))
        if size > 2 * 1024 * 1024:
            failures.append({'path': name, 'reasons': ['source blob exceeds 2 MiB']})
            continue
        data = git('cat-file', 'blob', oid)
        total += len(data)
        issues = audit_blob(name, mode, data, serial, fonts)
        if issues:
            failures.append({'path': name, 'reasons': issues})
    print(json.dumps({'passed': not failures, 'files': len(records),
                      'bytes': total, 'failures': failures}, indent=2))
    return 1 if failures else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError):
        # Do not accidentally echo credentials through an exception message.
        raise SystemExit('Repository audit could not complete; check Git state and file access.')
