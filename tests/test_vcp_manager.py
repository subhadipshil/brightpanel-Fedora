"""Unit tests for VCP manager, feature codes, and value conversions."""

import unittest
from brightpanel.core.vcp_manager import (
    VCPCode,
    VCPValue,
    normalize_input_code,
    get_input_name,
    DEFAULT_PRESETS,
    PowerMode
)


class TestVCPManager(unittest.TestCase):
    def test_vcp_constants(self):
        self.assertEqual(VCPCode.BRIGHTNESS, 0x10)
        self.assertEqual(VCPCode.CONTRAST, 0x12)
        self.assertEqual(VCPCode.AUDIO_VOLUME, 0x62)
        self.assertEqual(VCPCode.INPUT_SOURCE, 0x60)
        self.assertEqual(VCPCode.POWER_MODE, 0xD6)

    def test_vcp_value_clamping(self):
        self.assertEqual(VCPValue.clamp(120), 100)
        self.assertEqual(VCPValue.clamp(-10), 0)
        self.assertEqual(VCPValue.clamp(50), 50)
        self.assertEqual(VCPValue.clamp(0), 0)
        self.assertEqual(VCPValue.clamp(100), 100)

    def test_vcp_value_percentage(self):
        v1 = VCPValue(code=0x10, current=50, max_value=100)
        self.assertEqual(v1.percentage, 50)

        v2 = VCPValue(code=0x10, current=150, max_value=300)
        self.assertEqual(v2.percentage, 50)

        v3 = VCPValue(code=0x10, current=0, max_value=0)
        self.assertEqual(v3.percentage, 0)

    def test_normalize_input_code(self):
        self.assertEqual(normalize_input_code("hdmi1"), 0x11)
        self.assertEqual(normalize_input_code("HDMI2"), 0x12)
        self.assertEqual(normalize_input_code("dp1"), 0x0F)
        self.assertEqual(normalize_input_code("dp2"), 0x10)
        self.assertEqual(normalize_input_code("usbc"), 0x1B)
        self.assertEqual(normalize_input_code("usb-c"), 0x1B)
        self.assertEqual(normalize_input_code("0x11"), 0x11)
        self.assertEqual(normalize_input_code("17"), 17)
        self.assertEqual(normalize_input_code(0x0F), 0x0F)
        self.assertIsNone(normalize_input_code("invalid_input_code"))

    def test_get_input_name(self):
        self.assertEqual(get_input_name(0x11), "HDMI 1")
        self.assertEqual(get_input_name(0x0F), "DisplayPort 1")
        self.assertEqual(get_input_name(0x1B), "USB-C / DisplayPort")
        self.assertEqual(get_input_name(0x99), "Input (0x99)")

    def test_presets(self):
        self.assertIn("daylight", DEFAULT_PRESETS)
        self.assertIn("reading", DEFAULT_PRESETS)
        self.assertIn("night", DEFAULT_PRESETS)
        self.assertEqual(DEFAULT_PRESETS["daylight"]["brightness"], 100)
        self.assertEqual(DEFAULT_PRESETS["reading"]["brightness"], 35)


if __name__ == "__main__":
    unittest.main()
