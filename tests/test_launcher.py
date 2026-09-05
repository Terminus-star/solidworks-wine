"""Exercise launch argument forwarding without starting Wine or SOLIDWORKS."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def launch(self, options, arguments=()):
        with tempfile.TemporaryDirectory(prefix='solidworks-launch-test-') as folder:
            base = Path(folder)
            prefix = base / 'prefix'
            prefix.mkdir()
            (prefix / 'system.reg').touch()
            application = base / 'Installed CAD' / 'SLDWORKS.exe'
            application.parent.mkdir()
            application.touch()
            wine = base / 'wine'
            wine.write_text('#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n')
            wine.chmod(0o700)
            env = os.environ.copy()
            env.update(WINEPREFIX=str(prefix), WINE_BIN=str(wine),
                       SOLIDWORKS_LOG_DIR=str(base / 'logs'))
            result = subprocess.run(
                ['bash', str(ROOT / 'bin/run-solidworks.sh'), *options,
                 '--exe', str(application), '--', *arguments],
                env=env, text=True, capture_output=True, timeout=10, check=True,
            )
            invocation = json.loads(next(line for line in result.stdout.splitlines()
                                         if line.startswith('["')))
            self.assertEqual(invocation[0], str(application))
            return invocation[1:]

    def test_normal_launch_has_no_extra_mode(self):
        self.assertEqual(self.launch([]), [])

    def test_no_splash_passes_only_empty_macro_switch(self):
        self.assertEqual(self.launch(['--no-splash']), ['/m'])

    def test_document_uses_normal_mode_not_macro_mode(self):
        document = r'C:\Models\Example Part.SLDPRT'
        self.assertEqual(self.launch(['--no-splash'], [document]), [document])

    def test_normal_launch_preserves_explicit_macro_arguments(self):
        arguments = ['/m', r'C:\Macros\Example.swp']
        self.assertEqual(self.launch([], arguments), arguments)

    def test_no_splash_does_not_change_explicit_macro_arguments(self):
        arguments = ['/m', r'C:\Macros\Example.swp']
        self.assertEqual(self.launch(['--no-splash'], arguments), arguments)


if __name__ == '__main__':
    unittest.main()
