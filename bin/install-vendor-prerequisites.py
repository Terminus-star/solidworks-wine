#!/usr/bin/env python3
"""Explicit, serialized vendor prerequisites; no license credential is needed."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from solidworks_wine.msi import MSI, helper_output, validate_product
from solidworks_wine.supervisor import ensure_idle, lock_prefix, supervise

PACKAGES = (
    ('VBA 7.1', 'PreReqs/VBA/vba71.msi'),
    ('VBA English resources', 'PreReqs/VBA/vba71_1033.msi'),
    ('VSTA 2022', 'PreReqs/VSTA17/vsta_setup.exe'),
    ('CEF for SOLIDWORKS', 'swcef/CEF for SOLIDWORKS Applications.msi'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', action='store_true')
    mode.add_argument('--install', action='store_true')
    args = parser.parse_args()
    media = Path(os.environ['SOLIDWORKS_FULL_MEDIA_DIR']).resolve()
    plan = [{'name': name, 'path': str(media / path), 'present': (media / path).is_file()}
            for name, path in PACKAGES]
    if args.plan:
        print(json.dumps(plan, indent=2))
        return 0 if all(item['present'] for item in plan) else 1
    if not all(item['present'] for item in plan):
        raise ValueError('Vendor prerequisites missing; inspect --plan and complete your media')
    wine = os.environ['WINE']
    helper = ROOT / 'build/msi-tool.exe'
    prefix = Path(os.environ['WINEPREFIX']).resolve()
    if not (prefix / 'system.reg').is_file() or not helper.is_file():
        raise ValueError('First build helpers and initialize the dedicated prefix')
    os.umask(0o077)
    logs = Path(os.environ['SOLIDWORKS_LOG_DIR'])
    logs.mkdir(parents=True, exist_ok=True)
    with lock_prefix(prefix):
        ensure_idle(prefix)
        validate_product(MSI(ROOT, media).plan()['product'],
                         json.loads((ROOT / 'reproducibility.json').read_text())['target'])
        directory = Path(tempfile.mkdtemp(prefix='vendor-prerequisites-', dir=logs))
        results = []
        print('Private prerequisite evidence:', directory, flush=True)
        for index, item in enumerate(plan):
            run = directory / str(index + 1)
            run.mkdir()
            package = Path(item['path'])
            product = None
            if package.suffix == '.msi':
                query = helper_output([wine, str(helper), 'query', str(package),
                    "SELECT `Property`, `Value` FROM `Property` WHERE `Property` = 'ProductCode'"], check=True)
                product = dict(line.split('\t', 1) for line in query.stdout.splitlines() if '\t' in line)['ProductCode']
                command = [wine, str(helper), 'install-prerequisite', str(package),
                           str(run / 'msi.private.log'), 'REBOOT=ReallySuppress']
            else:
                # Vendor VSTA bootstrapper; passive UI leaves progress visible.
                command = [wine, str(package), '/install', '/passive', '/norestart',
                           '/log', 'Z:' + str(run / 'msi.private.log').replace('/', '\\')]
            print('Installing:', item['name'], flush=True)
            rc = supervise(command, '', run, prefix, timeout=1200, idle_timeout=300)
            valid = rc == 0
            if product:
                output = (run / 'console.private.log').read_text(errors='replace')
                codes = re.findall(r'MSI_RESULT=(\d+)', output)
                state = helper_output([wine, str(helper), 'verify', product])
                valid &= bool(codes) and int(codes[-1]) in (0, 3010) and 'product\t5' in state.stdout
            results.append({'name': item['name'], 'exit_code': rc, 'installer_verified': valid,
                            'verification': 'MSI result and product state' if product else 'bootstrapper exit only'})
            (directory / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
            if not valid:
                raise ValueError('Prerequisite failed; inspect private evidence before retrying')
        print('Prerequisite installers completed. VSTA integration still needs application-level testing.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(str(error))
