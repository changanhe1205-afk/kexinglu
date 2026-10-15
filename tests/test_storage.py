"""Failed copies must never activate an incomplete user data directory."""
from pathlib import Path
import tempfile
import sqlite3
import unittest
from unittest.mock import patch
import storage

class StorageMigrationTests(unittest.TestCase):
    def test_incomplete_copy_keeps_original_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';source.mkdir();target=Path(folder)/'target'
            with sqlite3.connect(source/'yingjianlu.db') as conn:
                conn.execute('CREATE TABLE records (title TEXT)')
                conn.execute("INSERT INTO records VALUES ('keep')")
            conn.close()
            (source/'photo.jpg').write_bytes(b'photo')
            original_copy=storage.shutil.copy2
            def copy(src,dst):
                if str(src).endswith('photo.jpg'):raise PermissionError('locked photo')
                return original_copy(src,dst)
            with patch.object(storage,'current_dir',return_value=str(source)), patch.object(storage.shutil,'copy2',side_effect=copy), patch.object(storage.config,'set_data_dir') as switch, patch.object(storage,'reload_all') as reload:
                ok,message=storage.migrate(str(target))
                self.assertFalse(ok);self.assertIn('未切换',message)
                switch.assert_not_called();reload.assert_not_called()
                self.assertEqual((source/'photo.jpg').read_bytes(),b'photo')

    def test_failed_destination_backup_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';source.mkdir();target=Path(folder)/'target';target.mkdir()
            (source/'yingjianlu.db').write_bytes(b'current')
            (target/'yingjianlu.db').write_bytes(b'existing')
            with patch.object(storage,'current_dir',return_value=str(source)), patch.object(storage.os,'replace',side_effect=PermissionError('locked')), patch.object(storage.config,'set_data_dir') as switch:
                ok,message=storage.migrate(str(target))
                self.assertFalse(ok);self.assertIn('无法备份',message)
                switch.assert_not_called()
                self.assertEqual((target/'yingjianlu.db').read_bytes(),b'existing')
