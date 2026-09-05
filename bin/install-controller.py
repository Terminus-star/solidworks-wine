#!/usr/bin/env python3
"""Plan, supervise, and verify the SOLIDWORKS Design MSI installation."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'lib'))
from solidworks_wine.credentials import read_serial, read_log, redact, redact_run
from solidworks_wine.msi import MSI, validate_product
from solidworks_wine.media import missing_toolbox_files, spatial_payload_issues
from solidworks_wine.supervisor import ensure_idle, lock_prefix, supervise
from solidworks_wine.verification import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('plan', 'install', 'verify', 'log', 'redact-run'))
    parser.add_argument('--path', type=Path, help='Log file to show with serials redacted')
    parser.add_argument('--timeout', type=int, default=1800)
    parser.add_argument('--idle-timeout', type=int, default=240)
    args = parser.parse_args()
    os.umask(0o077)
    serial_path = Path(os.environ.get('SOLIDWORKS_SERIAL_FILE', ROOT / 'serial.txt'))
    if args.command == 'redact-run':
        if not args.path or not args.path.is_dir():
            parser.error('redact-run requires --path RUN_DIRECTORY')
        redact_run(args.path, read_serial(serial_path))
        return 0
    if args.command == 'log':
        if not args.path:
            parser.error('log requires --path')
        serial = read_serial(serial_path) if serial_path.exists() else ''
        print(redact(read_log(args.path), serial))
        return 0
    prefix = Path(os.environ['WINEPREFIX']).resolve()
    media = Path(os.environ.get('SOLIDWORKS_FULL_MEDIA_DIR', ROOT / 'full-media'))
    msi = MSI(ROOT, media)
    lock = lock_prefix(prefix)
    if args.command == 'install':
        ensure_idle(prefix)
    plan = msi.plan()
    if args.command == 'install':
        validate_product(plan['product'], json.loads((ROOT / 'reproducibility.json').read_text())['target'])
    plan['missing_media'] = missing_toolbox_files(media)
    plan['compatibility'] = {
        'dll_overrides': os.environ.get('WINEDLLOVERRIDES', ''),
        'registration_workaround': os.environ.get('SOLIDWORKS_MSI_IGNORE_REGISTRATION_DEBUGGER_INACTIVE', ''),
        'spatial_preextracted': os.environ.get('SOLIDWORKS_MSI_SPATIAL_IOP_PREEXTRACTED', ''),
    }
    if args.command == 'plan':
        print(json.dumps(plan, indent=2))
        return 0
    if args.command == 'verify':
        report = verify(msi, prefix, plan)
        print(json.dumps(report, indent=2))
        return 0 if report['verified'] else 1
    if plan['missing_media']:
        raise ValueError(f"Missing {len(plan['missing_media'])} Toolbox archives. Complete the media download first; use --plan to list them.")
    # Preparation is inside the prefix lock, so a second controller cannot
    # overwrite resources while the first controller is installing them.
    subprocess.run(['bash', str(ROOT / 'bin/prepare-payloads.sh')], check=True, timeout=240)
    archive = media / 'swwi/data/spatialiop.zip'
    target = prefix / 'drive_c/Program Files/SOLIDWORKS Corp/SOLIDWORKS/spiop/files'
    issues = spatial_payload_issues(archive, target)
    if issues:
        raise ValueError(f'Spatial IOP payload has {len(issues)} missing/wrong-sized files; re-extract {archive} into {target}.')
    os.environ['SOLIDWORKS_MSI_SPATIAL_IOP_PREEXTRACTED'] = '1'
    plan['compatibility']['spatial_preextracted'] = '1'
    serial = read_serial(serial_path)
    logs = Path(os.environ.get('SOLIDWORKS_LOG_DIR', ROOT / 'logs'))
    directory = logs / ('install-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    directory.mkdir(parents=True, mode=0o700)
    (directory / 'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    properties = ' '.join([
        'INSTALLDIR="C:\\Program Files\\SOLIDWORKS Corp\\SOLIDWORKS"',
        'ADDLOCAL=' + ','.join(plan['features']), 'OFFICEOPTION=0',
        'TOOLBOXFOLDER="C:\\SWData"', 'ENABLEPERFORMANCE=0',
        'MSIFASTINSTALL=4', 'REBOOT=ReallySuppress', f'TRANSFORMS="{msi.transform}"',
    ])
    print(f"Installing {plan['product']['ProductName']}: {len(plan['features'])} core/default features.", flush=True)
    print(f"Evidence directory: {directory}", flush=True)
    rc = None
    try:
        rc = supervise(msi.command('install', msi.package, directory / 'msi.private.log', properties),
                       serial, directory, prefix, args.timeout, args.idle_timeout)
    finally:
        redact_run(directory, serial)
    text = (directory / 'console.log').read_text()
    codes = re.findall(r'MSI_RESULT=(\d+)', text)
    report = verify(msi, prefix, plan)
    report['msi_result'] = int(codes[-1]) if codes else None
    report['installer_exit_code'] = rc
    report['verified'] &= rc == 0 and report['msi_result'] in (0, 3010)
    (directory / 'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f"MSI result: {report['msi_result']}; verified installation: {report['verified']}")
    print(f"Report: {directory / 'verification.json'}")
    return 0 if report['verified'] else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f'install-controller: {exc}', file=sys.stderr)
        raise SystemExit(1)
