"""Unit tests for BrightPanel D-Bus daemon logic."""

import json
import unittest
from brightpanel.daemon.service import BrightPanelDaemon


class TestDaemon(unittest.TestCase):
    def setUp(self):
        self.daemon = BrightPanelDaemon(mock_mode=True)
        self.daemon.initialize()

    def tearDown(self):
        self.daemon.queue.stop()

    def test_get_monitors_json(self):
        json_str = self.daemon.get_monitors_json()
        data = json.loads(json_str)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)
        self.assertEqual(data[0]["display_num"], 1)

    def test_set_and_get_brightness(self):
        ok = self.daemon.set_brightness(1, 92)
        self.assertTrue(ok)
        val = self.daemon.get_brightness(1)
        self.assertEqual(val, 92)

    def test_set_contrast(self):
        ok = self.daemon.set_contrast(1, 68)
        self.assertTrue(ok)
        mon = self.daemon.get_monitor_by_num(1)
        self.assertIsNotNone(mon)
        self.assertEqual(mon.current_contrast, 68)

    def test_apply_preset(self):
        ok = self.daemon.apply_preset("reading")
        self.assertTrue(ok)
        mon1 = self.daemon.get_monitor_by_num(1)
        self.assertEqual(mon1.current_brightness, 35)

    def test_doctor_report(self):
        rep_json = self.daemon.get_doctor_report_json()
        report = json.loads(rep_json)
        self.assertIsInstance(report, list)
        self.assertGreaterEqual(len(report), 4)


if __name__ == "__main__":
    unittest.main()
