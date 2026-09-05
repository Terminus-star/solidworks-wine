"""Source-only portability, credential, packaging and build-recipe tests."""
import contextlib
import ast
import hashlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from solidworks_wine.desktop import render
from solidworks_wine.msi import validate_product
from solidworks_wine.repository import audit_blob


def script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'bin' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReproducibilityTests(unittest.TestCase):
    def test_all_python_sources_parse(self):
        for directory in ('bin', 'lib', 'tests'):
            for path in (ROOT / directory).rglob('*.py'):
                ast.parse(path.read_text(), filename=str(path))

    def test_documentation_relative_links_resolve(self):
        paths = list(ROOT.glob('*.md')) + list((ROOT / 'docs').glob('*.md'))
        for document in paths:
            for target in re.findall(r'\]\(([^\s)]+)\)', document.read_text()):
                if '://' in target or target.startswith('#'):
                    continue
                path = target.split('#', 1)[0]
                self.assertTrue((document.parent / path).exists(), f'{document.name}: {path}')

    def test_vendor_plan_needs_neither_wine_nor_serial(self):
        with tempfile.TemporaryDirectory() as folder:
            env = dict(os.environ, SOLIDWORKS_FULL_MEDIA_DIR=folder, WINE_BIN='/nonexistent/wine')
            result = subprocess.run(['bash', str(ROOT / 'bin/install-vendor-prerequisites.sh'), '--plan'],
                                    env=env, text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 1)
            plan = json.loads(result.stdout)
            self.assertEqual(len(plan), 4)
            self.assertTrue(all(not item['present'] for item in plan))

    def test_manifest_references_existing_files(self):
        manifest = json.loads((ROOT / 'reproducibility.json').read_text())
        self.assertEqual(manifest['wine']['version'], '9.22')
        self.assertEqual(len(manifest['wine']['source_sha256']), 64)
        for filename in manifest['wine']['patches']:
            self.assertTrue((ROOT / filename).is_file())

    def test_build_recipe_keeps_graphics_and_classic_32bit_msi(self):
        commands = script('build-wine-runtime').build_commands(Path('/source'), Path('/work'), Path('/runtime'), 4)
        self.assertIn('--enable-win64', commands[0][1])
        self.assertIn('--with-wine64=/work/build64', commands[2][1])
        self.assertIn('--without-mingw', commands[2][1])
        for index in (0, 2):
            self.assertIn('--with-opengl', commands[index][1])
            self.assertIn('--with-x', commands[index][1])
            self.assertIn('--with-gnutls', commands[index][1])

    def test_archive_rejects_traversal_absolute_and_escaping_links(self):
        builder = script('build-wine-runtime')
        for name, link in (('../outside', None), ('/absolute', None), ('wine-9.22/link', '../../outside')):
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode='w') as archive:
                member = tarfile.TarInfo(name)
                if link:
                    member.type, member.linkname = tarfile.SYMTYPE, link
                archive.addfile(member)
            data.seek(0)
            with tarfile.open(fileobj=data) as archive, self.assertRaises(ValueError):
                builder.safe_members(archive, 'wine-9.22')

    def test_wrong_source_hash_is_rejected_without_extraction(self):
        builder = script('build-wine-runtime')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            archive = root / 'wine.tar.xz'
            archive.write_bytes(b'not the official source')
            manifest = json.loads((ROOT / 'reproducibility.json').read_text())
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                builder.prepare(manifest, root / 'work', archive)
            self.assertFalse((root / 'work/wine-9.22').exists())

    def test_build_timeout_stops_process_group(self):
        builder = script('build-wine-runtime')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            code = 'import os,time\npid=os.fork()\nif pid: print(pid,flush=True)\ntime.sleep(20)'
            with (root / 'output').open('wb') as output:
                with self.assertRaises(subprocess.TimeoutExpired):
                    builder.run_build_step([sys.executable, '-c', code], root, output, 0.5)
            child = int((root / 'output').read_text().strip())
            status = Path(f'/proc/{child}/stat')
            for _ in range(20):
                if not status.exists() or status.read_text().split()[2] == 'Z':
                    break
                time.sleep(0.05)
            else:
                self.fail('Compiler descendant still running after timeout')

    def test_exact_msi_release_gate(self):
        target = json.loads((ROOT / 'reproducibility.json').read_text())['target']
        valid = {'ProductCode': target['core_product_code'], 'ProductVersion': target['msi_version']}
        validate_product(valid, target)
        with self.assertRaises(ValueError):
            validate_product(dict(valid, ProductVersion='different'), target)
        with self.assertRaises(ValueError):
            validate_product(dict(valid, ProductCode='different'), target)

    def test_serial_writer_is_private_and_preserves_existing_file(self):
        serial = '1' * 16 + 'A' * 8
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / 'serial.txt'
            env = dict(os.environ, SOLIDWORKS_SERIAL_FILE=str(destination))
            command = [sys.executable, str(ROOT / 'bin/set-serial.py'), '--from-stdin']
            result = subprocess.run(command, env=env, input=serial.lower(), text=True,
                                    capture_output=True, timeout=5, check=True)
            self.assertEqual(destination.read_text().strip(), serial)
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
            self.assertNotIn(serial, result.stdout + result.stderr)
            result = subprocess.run(command, env=env, input='invalid', text=True,
                                    capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(destination.read_text().strip(), serial)

    def test_audit_rejects_artifacts_even_disguised_as_source(self):
        for name, data in [('prefix/user.reg', b'registry'), ('docs/note.md', b'MZbinary'),
                           ('bin/read.py', b'\x7fELFbinary'), ('assets/solidworks.png', b'icon')]:
            self.assertTrue(audit_blob(name, '100644', data))
        self.assertTrue(audit_blob('README.md', '120000', b'/private/path'))
        self.assertEqual(audit_blob('README.md', '100644', b'Ordinary documentation'), [])

    def test_audit_detects_serial_variants_and_tokens_without_echoing_them(self):
        serial = '1' * 16 + 'A' * 8
        spaced = ' '.join(serial[i:i+4] for i in range(0, 24, 4))
        for value in (serial, spaced, serial[:16]):
            for encoding in ('utf-8', 'utf-16-le', 'utf-16-be'):
                reasons = audit_blob('docs/note.md', '100644', value.encode(encoding), serial)
                self.assertIn('contains local license material', reasons)
                self.assertNotIn(serial, str(reasons))
        token = 'ghp_' + 'a' * 36
        self.assertIn('possible authentication credential', audit_blob('docs/note.md', '100644', token.encode()))

    def test_font_hash_required(self):
        data = b'fake font fixture'
        self.assertTrue(audit_blob('assets/fonts/selawk.ttf', '100644', data))
        self.assertEqual(audit_blob('assets/fonts/selawk.ttf', '100644', data,
                                   font_hashes={'selawk.ttf': hashlib.sha256(data).hexdigest()}), [])

    def test_auditor_reads_staged_blob_not_cleaned_working_copy(self):
        auditor = script('audit-repository')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(root)], check=True)
            (root / 'README.md').write_text('1' * 16 + 'A' * 8)
            subprocess.run(['git', '-C', str(root), 'add', 'README.md'], check=True)
            (root / 'README.md').write_text('clean working copy')
            with patch.object(auditor, 'ROOT', root), patch.object(sys, 'argv', ['audit', '--staged']), \
                    patch.dict(os.environ, SOLIDWORKS_SERIAL_FILE=str(root / 'absent')), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(auditor.main(), 1)
            self.assertFalse(json.loads(output.getvalue())['passed'])

    def test_generated_desktop_passes_freedesktop_validator(self):
        if not shutil.which('desktop-file-validate'):
            self.skipTest('desktop-file-validate not installed')
        with tempfile.TemporaryDirectory(prefix='solidworks desktop ') as folder:
            root = Path(folder)
            entry = root / 'test.desktop'
            entry.write_text(render(root, root / 'prefix with spaces', root / 'runtime/bin/wine'))
            subprocess.run(['desktop-file-validate', str(entry)], check=True, capture_output=True)
            self.assertIn('--no-splash', entry.read_text())
            self.assertIn('Icon=applications-engineering', entry.read_text())

    def test_desktop_exec_roundtrip_with_glib(self):
        # Optional local integration check using the desktop's actual parser.
        python = '/usr/bin/python3'
        gio_env = dict(os.environ)
        for key in ('GI_TYPELIB_PATH', 'LD_LIBRARY_PATH', 'GIO_EXTRA_MODULES'):
            if '/nix/store/' in gio_env.get(key, ''):
                gio_env.pop(key)
        probe = subprocess.run([python, '-c', 'from gi.repository import Gio'],
                               env=gio_env, capture_output=True, timeout=5)
        if probe.returncode:
            self.skipTest('Python GObject/Gio bindings not installed')
        with tempfile.TemporaryDirectory(prefix='solidworks desktop ') as folder:
            root = Path(folder) / 'CAD 100% $test `tick` "quote" café'
            (root / 'bin').mkdir(parents=True)
            output = root / 'launched.json'
            launcher = root / 'bin/run-solidworks.sh'
            launcher.write_text('#!' + sys.executable + '\nimport json,os,sys\n'
                                'from pathlib import Path\nPath(' + repr(str(output)) + ').write_text('
                                'json.dumps([os.environ["WINEPREFIX"],os.environ["WINE_BIN"],sys.argv[1:]]))\n')
            launcher.chmod(0o755)
            prefix, wine = root / 'private prefix', root / 'runtime/bin/wine'
            entry = root / 'test.desktop'
            entry.write_text(render(root, prefix, wine))
            subprocess.run([python, '-c', 'from gi.repository import Gio; import sys; '
                            'app=Gio.DesktopAppInfo.new_from_filename(sys.argv[1]); '
                            'assert app is not None; app.launch([], None)', str(entry)],
                           check=True, capture_output=True, timeout=5, env=gio_env)
            for _ in range(50):
                if output.exists():
                    break
                time.sleep(0.02)
            self.assertEqual(json.loads(output.read_text()), [str(prefix), str(wine), ['--no-splash']])


if __name__ == '__main__':
    unittest.main()
