#!/usr/bin/env python3
"""Download only the missing Toolbox payloads via the authorized vendor session."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from solidworks_wine.downloads import download_package, request_template, toolbox_packages
from solidworks_wine.supervisor import lock_prefix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--session-log', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.destination.mkdir(parents=True, exist_ok=True)
    try:
        with lock_prefix(args.destination):
            packages = toolbox_packages(args.catalog)
            template = request_template(args.session_log)
            print(f"Downloading {len(packages)} catalogued packages, {sum(p['size'] for p in packages)} bytes; two connections", flush=True)
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(lambda p: download_package(template, p, args.destination), packages))
    except (ValueError, OSError) as exc:
        # Network exceptions are sanitized inside downloads.py; never print URLs.
        print(f'download-toolbox: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
