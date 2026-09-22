"""Unit tests for display detection and ddcutil output parsing."""

import unittest
from brightpanel.core.detector import DisplayDetector, DisplayInfo

SAMPLE_DDCUTIL_DETECT = """
Display 1
   I2C bus:  /dev/i2c-4
   DRM connector:           card0-DP-1
   EDID synopsis:
      Mfg id:               DEL - Dell Inc.
      Model:                DELL U2720Q
      Product code:         53372  (0xd07c)
      Serial number:        CN05R90NTV2000880344
      Binary serial number: 12345678 (0x00bc614e)
      Manufacture year:     2020,  Week: 34
   VCP version:         2.1

Display 2
   I2C bus:  /dev/i2c-5
   DRM connector:           card0-HDMI-A-1
   EDID synopsis:
      Mfg id:               GSM - LG Electronics
      Model:                LG UltraFine
      Product code:         23456  (0x5ba0)
      Serial number:        108NTXF9K219
   VCP version:         2.2

Invalid display
   I2C bus:  /dev/i2c-1
   Controls: None
"""


class TestDisplayDetector(unittest.TestCase):
    def setUp(self):
        self.detector = DisplayDetector()

    def test_parse_sample_output(self):
        displays = self.detector._parse_ddcutil_output(SAMPLE_DDCUTIL_DETECT)
        self.assertEqual(len(displays), 2)

        d1 = displays[0]
        self.assertEqual(d1.display_num, 1)
        self.assertEqual(d1.bus_num, 4)
        self.assertEqual(d1.model, "DELL U2720Q")
        self.assertEqual(d1.mfg_id, "DEL - Dell Inc.")
        self.assertEqual(d1.serial, "CN05R90NTV2000880344")
        self.assertEqual(d1.connector, "card0-DP-1")
        self.assertTrue(d1.is_ddc_supported)

        d2 = displays[1]
        self.assertEqual(d2.display_num, 2)
        self.assertEqual(d2.bus_num, 5)
        self.assertEqual(d2.model, "LG UltraFine")
        self.assertEqual(d2.connector, "card0-HDMI-A-1")

    def test_mock_displays(self):
        displays = self.detector.detect(force_refresh=True, allow_mock=True)
        self.assertGreaterEqual(len(displays), 2)
        self.assertTrue(any(d.is_mock for d in displays))
        first = displays[0]
        self.assertTrue(first.display_name)
        d_dict = first.to_dict()
        self.assertIn("display_name", d_dict)
        self.assertIn("current_brightness", d_dict)

    def test_display_info_summary(self):
        info = DisplayInfo(
            id="test-1",
            display_num=1,
            bus_num=3,
            model="Dell U2720Q",
            connector="DP-1",
            current_brightness=80
        )
        self.assertIn("Dell U2720Q", info.summary)
        self.assertIn("80%", info.summary)
        self.assertIn("/dev/i2c-3", info.summary)


if __name__ == "__main__":
    unittest.main()
