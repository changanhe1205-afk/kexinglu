import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import config
from cloud_profile import ProfileRepository
from cloud_client import CloudError


class Client:
    uid = 'account-a'
    def __init__(self): self.calls = []; self.fail = False
    def request(self, path, body=None, **kwargs):
        self.calls.append((path, body))
        if self.fail: raise CloudError('offline')
        return {'user_metadata': {'kexinglu_profile': {'nickname': '手机昵称', 'cover': 'preset:sea.svg'}}}


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_cache = config._cache
        self.patch = patch.object(config, 'CONFIG_PATH', str(Path(self.temp.name) / 'settings.json'))
        self.patch.start(); config._cache = {}
        self.client = Client(); self.repo = ProfileRepository(self.client)
    def tearDown(self):
        self.patch.stop(); config._cache = self.old_cache; self.temp.cleanup()
    def test_metadata_roundtrip_preserves_cover(self):
        profile = self.repo.load()
        self.repo.save({**profile, 'nickname': '桌面昵称', 'birthday': '2000-02-29'})
        self.assertEqual(self.client.calls[-1][1]['data']['kexinglu_profile']['cover'], 'preset:sea.svg')
        self.assertFalse(self.repo.local()['pending'])
    def test_failed_save_retains_pending_and_account_isolation(self):
        self.client.fail = True
        with self.assertRaises(CloudError): self.repo.save({'nickname': '未上传'})
        self.assertTrue(self.repo.local()['pending'])
        self.client.uid = 'account-b'
        self.assertEqual(ProfileRepository(self.client).local(), {})
        with self.assertRaises(CloudError): self.repo.save({'nickname': '不能串号'})
    def test_invalid_birthday_does_not_write(self):
        with self.assertRaises(CloudError): self.repo.save({'birthday': '2001-02-29'})
        self.assertEqual(self.repo.local(), {})
    def test_avatar_uses_shared_asset_protocol(self):
        pointer = {'$asset': 'a' * 64 + '.jpg'}
        with patch('cloud_media.upload', return_value={'image': pointer}):
            self.repo.save({'avatar': 'test.jpg'})
        self.assertEqual(self.client.calls[-1][1]['data']['kexinglu_profile']['avatar'], pointer)
