"""Unit tests for brightpanel CLI commands."""

import unittest
from brightpanel.cli.main import build_parser, filter_monitors
from brightpanel.core.detector import DisplayInfo


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()
        self.monitors = [
            DisplayInfo(
                id="ddc-1-i2c-4",
                display_num=1,
                bus_num=4,
                model="Dell U2720Q",
                connector="DP-1",
                current_brightness=75
            ),
            DisplayInfo(
                id="ddc-2-i2c-5",
                display_num=2,
                bus_num=5,
                model="LG UltraFine",
                connector="HDMI-1",
                current_brightness=50
            ),
        ]

    def test_parser_subcommands(self):
        args_list = self.parser.parse_args(["list", "--mock"])
        self.assertEqual(args_list.command, "list")
        self.assertTrue(args_list.mock)

        args_set = self.parser.parse_args(["set", "80", "-m", "1"])
        self.assertEqual(args_set.command, "set")
        self.assertEqual(args_set.value, 80)
        self.assertEqual(args_set.monitor, "1")

        args_inc = self.parser.parse_args(["inc", "10"])
        self.assertEqual(args_inc.command, "inc")
        self.assertEqual(args_inc.step, 10)

        args_preset = self.parser.parse_args(["preset", "reading"])
        self.assertEqual(args_preset.command, "preset")
        self.assertEqual(args_preset.name, "reading")

        args_doctor = self.parser.parse_args(["doctor", "--json"])
        self.assertEqual(args_doctor.command, "doctor")
        self.assertTrue(args_doctor.json)

    def test_filter_monitors(self):
        # By index
        res1 = filter_monitors(self.monitors, "1")
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0].display_num, 1)

        # By model substring
        res_dell = filter_monitors(self.monitors, "dell")
        self.assertEqual(len(res_dell), 1)
        self.assertEqual(res_dell[0].model, "Dell U2720Q")

        # By all
        res_all = filter_monitors(self.monitors, "all")
        self.assertEqual(len(res_all), 2)


if __name__ == "__main__":
    unittest.main()
