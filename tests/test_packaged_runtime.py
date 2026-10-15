"""First-run host resolution and secure certificate fallback regressions."""
from pathlib import Path
import os
import ssl
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime_bootstrap import configure_desktop_runtime, bind_bundled_runtime
from network_tls import https_context


class PackagedRuntimeTests(unittest.TestCase):
    def test_fallback_resolver_cannot_download_even_if_view_path_is_lost(self):
        import flet_desktop
        import urllib.request
        with tempfile.TemporaryDirectory() as folder:
            client=Path(folder)/'flet_desktop/app/flet'
            for name in ('flet.exe','flutter_windows.dll','data/icudtl.dat','data/app.so'):
                target=client/name;target.parent.mkdir(parents=True,exist_ok=True);target.touch()
            with patch.object(sys,'frozen',True,create=True), patch.object(sys,'_MEIPASS',folder,create=True), \
                 patch.object(sys,'platform','win32'), patch.dict(os.environ), \
                 patch.object(flet_desktop,'ensure_client_cached'), \
                 patch.object(urllib.request,'urlopen',side_effect=AssertionError('Network forbidden')):
                bind_bundled_runtime()
                os.environ.pop('FLET_VIEW_PATH')
                self.assertEqual(flet_desktop.ensure_client_cached(),client.parent)
                (client/'flet.exe').unlink()
                with self.assertRaisesRegex(RuntimeError,'重新安装完整安装包'):
                    flet_desktop.ensure_client_cached()

    def test_weather_certificate_failure_is_optional(self):
        import urllib.error
        import weather
        failure=urllib.error.URLError(ssl.SSLCertVerificationError(1,'unable to get local issuer certificate'))
        with patch('urllib.request.urlopen',side_effect=failure):
            self.assertIsNone(weather._get_json('https://example.invalid'))

    def test_frozen_runtime_uses_bundle_not_existing_environment_or_home(self):
        with tempfile.TemporaryDirectory() as folder:
            client=Path(folder)/'flet_desktop/app/flet'
            for name in ('flet.exe','flutter_windows.dll','data/icudtl.dat','data/app.so'):
                target=client/name;target.parent.mkdir(parents=True,exist_ok=True);target.touch()
            with patch.object(sys,'frozen',True,create=True), patch.object(sys,'_MEIPASS',folder,create=True), \
                 patch.object(sys,'platform','win32'), patch.dict(os.environ,{'FLET_VIEW_PATH':'missing'}):
                self.assertEqual(configure_desktop_runtime(),client)
                self.assertEqual(os.environ['FLET_VIEW_PATH'],str(client))

    def test_incomplete_bundle_fails_locally_instead_of_downloading(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(sys,'frozen',True,create=True), \
             patch.object(sys,'_MEIPASS',folder,create=True), patch.object(sys,'platform','win32'):
            with self.assertRaisesRegex(RuntimeError,'重新安装完整安装包'):
                configure_desktop_runtime()

    def test_https_without_system_roots_still_loads_bundled_roots(self):
        with patch.object(ssl.SSLContext,'load_default_certs',side_effect=OSError('empty store')):
            with self.assertLogs('network_tls',level='WARNING'):
                context=https_context()
        self.assertGreater(context.cert_store_stats()['x509_ca'],100)
        self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)

    def test_system_roots_are_added_to_public_roots(self):
        with patch.object(ssl.SSLContext,'load_default_certs') as load:
            context=https_context()
        load.assert_called_once()
        self.assertGreater(context.cert_store_stats()['x509_ca'],100)

if __name__=='__main__': unittest.main()
