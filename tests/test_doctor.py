"""Unit tests for Fedora system diagnostic doctor."""

import unittest
from brightpanel.core.doctor import SystemDoctor, DiagnosticItem


class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.doctor = SystemDoctor()

    def test_run_all_checks(self):
        checks = self.doctor.run_all_checks()
        self.assertIsInstance(checks, list)
        self.assertGreaterEqual(len(checks), 5)
        for c in checks:
            self.assertIsInstance(c, DiagnosticItem)
            self.assertIn(c.status, ("OK", "WARN", "FAIL"))
            d = c.to_dict()
            self.assertIn("name", d)
            self.assertIn("status", d)
            self.assertIn("message", d)

    def test_cli_report_generation(self):
        report = self.doctor.generate_cli_report()
        self.assertIn("BrightPanel System Doctor", report)
        self.assertIn("ddcutil Binary", report)
        self.assertIn("Kernel Module (i2c-dev)", report)


if __name__ == "__main__":
    unittest.main()
