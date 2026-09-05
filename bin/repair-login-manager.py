#!/usr/bin/env python3
"""Repair the provided Login Manager MSI with the same bounds as the core MSI."""
from datetime import datetime
import json
import os
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from solidworks_wine.credentials import read_serial, redact_run
from solidworks_wine.msi import MSI, helper_output
from solidworks_wine.supervisor import ensure_idle, lock_prefix, supervise


def main():
    os.umask(0o077)
    prefix = Path(os.environ['WINEPREFIX'])
    with lock_prefix(prefix):
        ensure_idle(prefix)
        media = Path(os.environ['SOLIDWORKS_FULL_MEDIA_DIR'])
        msi = MSI(ROOT, media)
        package = media / 'swloginmgr/SOLIDWORKS Login Manager.msi'
        product = '{DFB580AD-E043-49A4-9380-F0D054E1C0FF}'
        state = helper_output(msi.command('verify', product)).stdout
        properties = 'REBOOT=ReallySuppress'
        if 'product\t5' in state:
            properties += ' REINSTALL=ALL REINSTALLMODE=vomus'
        directory = Path(os.environ.get('SOLIDWORKS_LOG_DIR', ROOT / 'logs')) / ('login-manager-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        directory.mkdir(parents=True, mode=0o700)
        serial = read_serial(Path(os.environ['SOLIDWORKS_SERIAL_FILE']))
        print(f'Login Manager repair evidence: {directory}', flush=True)
        try:
            rc = supervise(msi.command('install', package, directory / 'msi.private.log', properties),
                           serial, directory, prefix, timeout=600, idle_timeout=240)
        finally:
            redact_run(directory, serial)
        state = helper_output(msi.command('verify', product)).stdout
        results = re.findall(r'MSI_RESULT=(\d+)', (directory / 'console.log').read_text())
        result = int(results[-1]) if results else None
        library = prefix / 'drive_c/Program Files/Common Files/SOLIDWORKS Shared/LoginManager/sldLoginManager.dll'
        valid = rc == 0 and result in (0, 3010) and 'product\t5' in state and library.is_file() and library.stat().st_size > 0
        report = dict(exit_code=rc, msi_result=result, product_state=state.strip(), verified=valid,
                      registration_workaround=os.environ.get('SOLIDWORKS_MSI_IGNORE_REGISTRATION_DEBUGGER_INACTIVE'))
        (directory / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
        print(report)
        return 0 if valid else 1


if __name__ == '__main__':
    raise SystemExit(main())
