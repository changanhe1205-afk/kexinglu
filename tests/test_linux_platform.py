import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import config
import platform_files
import runtime_bootstrap


class LinuxPlatformTests(unittest.TestCase):
    def test_xdg_paths_are_outside_application(self):
        with patch.object(sys,'platform','linux'), patch.object(sys,'frozen',True,create=True), patch.dict(os.environ,{'XDG_CONFIG_HOME':'/tmp/test-config','XDG_DATA_HOME':'/tmp/test-data'}):
            self.assertEqual(config._config_dir(),os.path.join('/tmp/test-config','kexinglu'))
            self.assertTrue(config.default_data_dir().endswith('kexinglu'))

    def test_opener_passes_special_characters_as_one_argument(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'a & b.txt';target.touch()
            with patch.object(sys,'platform','linux'),patch('platform_files.subprocess.Popen') as launch:
                platform_files.open_local(target)
                self.assertEqual(launch.call_args.args[0],['xdg-open',str(target.resolve())])
                self.assertNotIn('shell',launch.call_args.kwargs)

    def test_linux_frozen_host_is_local_only(self):
        with tempfile.TemporaryDirectory() as folder:
            host=Path(folder)/'flet_desktop/app/flet'
            for name in ('flet','lib/libflutter_linux_gtk.so','data/icudtl.dat'):
                p=host/name;p.parent.mkdir(parents=True,exist_ok=True);p.touch()
            with patch.object(sys,'platform','linux'),patch.object(sys,'frozen',True,create=True),patch.object(sys,'_MEIPASS',folder,create=True),patch.dict(os.environ):
                self.assertEqual(runtime_bootstrap.configure_desktop_runtime(),host)
                self.assertEqual(os.environ['FLET_VIEW_PATH'],str(host))
