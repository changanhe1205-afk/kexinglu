"""Configuration upgrade tests. No access to real user data."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config


class BrandCompatibilityTests(unittest.TestCase):
    def test_legacy_data_and_new_install(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"LOCALAPPDATA": root}), patch.object(sys, "frozen", True, create=True):
            self.assertEqual(config.default_data_dir(), str(Path(root) / "客行录"))
            legacy = Path(root) / "影笺录"
            legacy.mkdir()
            self.assertEqual(config.default_data_dir(), str(legacy))
            current = Path(root) / "客行录"
            current.mkdir()
            self.assertEqual(config.default_data_dir(), str(current))

    def test_old_config_is_read_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"APPDATA": root}), patch.object(sys, "frozen", True, create=True):
            old = Path(root) / "影笺录" / "settings.json"
            old.parent.mkdir()
            original = json.dumps({"data_dir": "D:/MyJournal"})
            old.write_text(original, encoding="utf-8")
            new = str(Path(root) / "客行录" / "settings.json")
            with patch.object(config, "CONFIG_PATH", new), patch.object(config, "_cache", None):
                self.assertEqual(config.data_dir(), "D:/MyJournal")
                config.set_data_dir("D:/NewJournal")
                self.assertEqual(old.read_text(encoding="utf-8"), original)
                config._cache = None
                self.assertEqual(config.data_dir(), os.path.abspath("D:/NewJournal"))

    def test_development_config_stays_separate(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"APPDATA": root}), patch.object(sys, "frozen", False, create=True):
            self.assertEqual(Path(config._config_dir()).name, "客行录-dev")
            self.assertEqual(Path(config._legacy_config_path()).parent.name, "影笺录-dev")


if __name__ == "__main__":
    unittest.main()
