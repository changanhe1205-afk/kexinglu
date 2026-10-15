from pathlib import Path
import tempfile
import unittest
from app_version import VERSION
from release_integrity import REQUIRED, write_manifest, verify_manifest


class ReleaseIntegrityTests(unittest.TestCase):
    def test_mixed_or_modified_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in REQUIRED:
                file=root/name
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes(b'fixture')
            write_manifest(root)
            verify_manifest(root,VERSION)
            with self.assertRaisesRegex(ValueError,'版本不一致'):
                verify_manifest(root,'2.5.1')
            (root/REQUIRED[0]).write_bytes(b'older executable')
            with self.assertRaisesRegex(ValueError,'构建记录不一致'):
                verify_manifest(root,VERSION)
