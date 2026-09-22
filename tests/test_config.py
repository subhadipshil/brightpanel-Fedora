"""Unit tests for configuration manager."""

import os
import shutil
import tempfile
import unittest
from brightpanel.core.config import ConfigManager, ConfigData


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ConfigManager(config_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_config(self):
        data = self.manager.data
        self.assertFalse(data.sync_all)
        self.assertEqual(data.step_size, 5)
        self.assertIn("daylight", data.presets)
        self.assertEqual(data.presets["daylight"]["brightness"], 100)

    def test_save_and_reload(self):
        self.manager.set_preset("custom_work", 60, 65)
        self.assertTrue(os.path.exists(self.manager.config_file))

        new_manager = ConfigManager(config_dir=self.temp_dir)
        preset = new_manager.get_preset("custom_work")
        self.assertIsNotNone(preset)
        self.assertEqual(preset["brightness"], 60)
        self.assertEqual(preset["contrast"], 65)


if __name__ == "__main__":
    unittest.main()
