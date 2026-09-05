#!/usr/bin/env python3
"""Validate vendor packages and stage only their catalogued nested Toolbox ZIPs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from solidworks_wine.downloads import check_package, toolbox_packages
from solidworks_wine.media import missing_toolbox_files
from solidworks_wine.supervisor import lock_prefix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--packages', type=Path, required=True)
    parser.add_argument('--media', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    packages = toolbox_packages(args.catalog)
    # Validate the complete set before modifying the actual installation media.
    for package in packages:
        if not check_package(args.packages / package['name'], package):
            raise ValueError(f"Package not verified: {package['name']}")
    target = args.media / 'toolbox'
    target.mkdir(exist_ok=True)
    report = []
    with lock_prefix(args.media):
        for package in packages:
            expected = package['name'][len('Toolbox_'):-4] + '.zip'
            destination = target / expected
            path = args.packages / package['name']
            with zipfile.ZipFile(path) as archive:
                members = archive.infolist()
                if len(members) != 1 or members[0].filename.replace('\\', '/').lower() != '/toolbox/' + expected.lower():
                    raise ValueError(f"Unexpected package layout: {package['name']}")
                info = members[0]
                if info.file_size > 4 * package['size']:
                    raise ValueError('Unexpected decompressed payload size')
                digest = hashlib.sha256()
                with tempfile.NamedTemporaryFile(dir=target, prefix=expected + '.', suffix='.part', delete=False) as output:
                    temporary = Path(output.name)
                    with archive.open(info) as source:
                        while chunk := source.read(1024 * 1024):
                            output.write(chunk)
                            digest.update(chunk)
                with zipfile.ZipFile(temporary) as payload:
                    if payload.testzip() is not None:
                        raise ValueError(f'Corrupt nested archive: {expected}')
                if destination.exists():
                    old_digest = hashlib.sha256()
                    with destination.open('rb') as current:
                        while chunk := current.read(1024 * 1024):
                            old_digest.update(chunk)
                    if old_digest.hexdigest() != digest.hexdigest():
                        raise ValueError(f'Existing target preserved: {destination}')
                else:
                    os.link(temporary, destination)
                temporary.unlink()
                report.append(dict(package=package['name'], size=package['size'],
                                   vendor_checksum=package['crc'], payload=expected,
                                   payload_sha256=digest.hexdigest()))
                print(f'Validated and staged toolbox/{expected}', flush=True)
    missing = missing_toolbox_files(args.media)
    if missing:
        raise ValueError('Media still lacks catalogued Toolbox files')
    (args.packages / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'All {len(report)} Toolbox archives validated; media preflight is complete.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(f'extract-toolbox: {exc}', file=sys.stderr)
        raise SystemExit(1)
