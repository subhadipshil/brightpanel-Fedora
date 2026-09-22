"""Unit tests for asynchronous I2C queue and debouncing engine."""

import time
import unittest
from brightpanel.core.detector import DisplayInfo
from brightpanel.core.i2c_queue import I2CCommandQueue
from brightpanel.core.vcp_manager import VCPCode


class TestI2CQueue(unittest.TestCase):
    def setUp(self):
        self.queue = I2CCommandQueue(debounce_interval=0.05)
        self.display = DisplayInfo(
            id="test-mock",
            display_num=1,
            bus_num=4,
            model="Test Display",
            is_mock=True
        )

    def tearDown(self):
        self.queue.stop()

    def test_cache_and_immediate_update(self):
        self.queue.set_brightness(self.display, 85)
        val = self.queue.get_cached_value(1, VCPCode.BRIGHTNESS)
        self.assertEqual(val, 85)

    def test_clamping_on_enqueue(self):
        self.queue.set_brightness(self.display, 150)
        self.assertEqual(self.queue.get_cached_value(1, VCPCode.BRIGHTNESS), 100)

        self.queue.set_brightness(self.display, -20)
        self.assertEqual(self.queue.get_cached_value(1, VCPCode.BRIGHTNESS), 0)

    def test_listener_notification(self):
        events = []

        def on_change(disp_num, vcp, val):
            events.append((disp_num, vcp, val))

        self.queue.add_listener(on_change)
        self.queue.set_brightness(self.display, 70)
        self.queue.set_contrast(self.display, 60)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0], (1, VCPCode.BRIGHTNESS, 70))
        self.assertEqual(events[1], (1, VCPCode.CONTRAST, 60))

        self.queue.remove_listener(on_change)
        self.queue.set_brightness(self.display, 30)
        self.assertEqual(len(events), 2)  # No new event after removal

    def test_debounced_execution(self):
        results = []

        def callback(success, val):
            results.append((success, val))

        # Enqueue multiple rapid changes simulating dragging a slider
        for v in [50, 55, 60, 65, 70, 75, 80]:
            self.queue.set_brightness(self.display, v, callback=callback)

        # Allow worker thread time to process
        time.sleep(0.3)

        self.assertGreaterEqual(len(results), 1)
        # The final processed value must be the last one: 80
        self.assertEqual(results[-1], (True, 80))


if __name__ == "__main__":
    unittest.main()
