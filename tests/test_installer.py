"""Regression checks for the failure modes seen on this host."""
import os
from pathlib import Path
import sys
import tempfile
import subprocess
import signal
import urllib.parse
import urllib.request
import unittest
import zipfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'lib'))
from solidworks_wine.credentials import redact
from solidworks_wine.msi import select_features, ROOTS, REQUIRED, helper_output
from solidworks_wine.supervisor import lock_prefix, supervise
from solidworks_wine.verification import verify, is_registry_source_marker
from solidworks_wine.media import spatial_payload_issues
from solidworks_wine.downloads import authorized_url, VendorRedirect


class InstallerTests(unittest.TestCase):
    def test_serial_redaction_handles_vendor_spacing(self):
        serial = '1' * 16 + 'A' * 8
        spaced = ' '.join(serial[i:i+4] for i in range(0, 24, 4))
        for value in (serial, spaced, spaced.lower(), serial[:16], spaced[:19]):
            self.assertNotIn(value, redact('Serial=' + value, serial))

    def test_core_descendants_selected_optional_branches_excluded(self):
        rows = [[name, '', '100', '0'] for name in ROOTS]
        rows += [[name, 'SolidWorks', '100', '0'] for name in REQUIRED if name not in ROOTS]
        rows += [['Optional', 'SolidWorks', '200', '0'], ['OptionalChild', 'Optional', '100', '0'],
                 ['NestedLibrary', 'ProgramFiles', '100', '0']]
        selected = select_features(rows)
        self.assertTrue(set(REQUIRED) <= set(selected))
        self.assertIn('NestedLibrary', selected)
        self.assertNotIn('OptionalChild', selected)

    def test_addons_only_msi_is_rejected(self):
        with self.assertRaises(ValueError):
            select_features([['FeatureWorks', '', '100', '0']])

    def test_prefix_lock_rejects_second_controller(self):
        with tempfile.TemporaryDirectory() as temp:
            first = lock_prefix(Path(temp))
            try:
                with self.assertRaises(ValueError):
                    lock_prefix(Path(temp))
            finally:
                first.close()

    def test_watchdog_stops_hung_process(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, WINESERVER='/bin/true'):
            with self.assertRaisesRegex(RuntimeError, 'no-install-progress'):
                supervise([sys.executable, '-c', 'import time; time.sleep(30)'],
                          '', Path(temp), Path(temp), timeout=10, idle_timeout=0.1)
            self.assertIn('"status": "stopped"', (Path(temp) / 'state.json').read_text())

    def test_success_code_without_core_files_is_rejected(self):
        class FakeMSI:
            def command(self, *args):
                return ['/bin/true']
        with tempfile.TemporaryDirectory() as temp:
            report = verify(FakeMSI(), Path(temp), {'product': {'ProductCode': 'test'}, 'features': []})
            self.assertFalse(report['verified'])

    def test_registry_source_marker_does_not_allow_actual_disk_sources(self):
        self.assertTrue(is_registry_source_marker(260, '02:\\Software\\Example\\Value'))
        self.assertFalse(is_registry_source_marker(256, '02:\\Software\\Example\\Value'))
        self.assertFalse(is_registry_source_marker(260, '01\\source.dll'))
        self.assertFalse(is_registry_source_marker(260, 'C:\\Program Files\\Example.dll'))

    def test_helper_output_does_not_wait_for_inherited_pipe_eof(self):
        code = 'import os,time\npid=os.fork()\nif pid: print(pid,flush=True)\nelse: time.sleep(5)'
        result = helper_output([sys.executable, '-c', code], timeout=3)
        child = int(result.stdout.strip())
        try:
            self.assertEqual(result.returncode, 0)
        finally:
            try:
                os.kill(child, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def test_spatial_audit_checks_middle_members_too(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with zipfile.ZipFile(root / 'payload.zip', 'w') as archive:
                for name in ('first', 'middle', 'last'):
                    archive.writestr(name, b'payload')
            for name in ('first', 'last'):
                (root / name).write_bytes(b'payload')
            self.assertEqual(spatial_payload_issues(root / 'payload.zip', root), ['middle'])

    def test_vendor_checksum_complements_every_byte(self):
        source = Path(__file__).resolve().parents[1] / 'native/media-checksum.c'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['gcc', '-O2', '-Wall', '-Wextra', '-Werror', str(source),
                            '-o', str(root / 'checksum')], check=True)
            for data in (b'', b'123456789', bytes(range(256)) * 300):
                value = 0xffffffff
                for byte in data:
                    value ^= byte
                    for _ in range(8):
                        value = (value >> 1) ^ (0xedb88320 if value & 1 else 0)
                    value ^= 0xffffffff
                (root / 'payload').write_bytes(data)
                actual = subprocess.check_output([str(root / 'checksum'), str(root / 'payload')], text=True)
                self.assertEqual(int(actual), value)

    def test_download_request_preserves_vendor_session(self):
        template = urllib.parse.urlsplit('http://im.solidworks.com/2026/GetDownloadURL.aspx?serial_number=opaque&filename=old.exe&domain=dl-ak.solidworks.com&subpath=old&explungulation=timestamp')
        package = dict(name='Toolbox_iso.exe', domain='dl-ak.solidworks.com', server='secured/sw2026/release')
        url = urllib.parse.urlsplit(authorized_url(template, package))
        self.assertEqual(url.scheme, 'https')
        fields = dict(urllib.parse.parse_qsl(url.query))
        self.assertEqual(fields['serial_number'], 'opaque')
        self.assertEqual(fields['filename'], package['name'])
        self.assertEqual(fields['explungulation'], 'timestamp')

    def test_download_rejects_external_redirect(self):
        request = urllib.request.Request('https://im.solidworks.com/2026/GetDownloadURL.aspx')
        with self.assertRaisesRegex(ValueError, 'outside expected vendor hosts'):
            VendorRedirect().redirect_request(request, None, 302, '', {}, 'https://example.com/file')


if __name__ == '__main__':
    unittest.main()
