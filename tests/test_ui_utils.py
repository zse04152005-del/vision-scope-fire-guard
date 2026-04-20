import unittest
from ui.utils import reorder_camera_order, filter_alarm_events


class TestUIUtils(unittest.TestCase):
    def test_reorder_camera_order(self):
        order = ["cam01", "cam02", "cam03"]
        new_order = reorder_camera_order(order, "cam01", "cam03")
        self.assertEqual(new_order, ["cam03", "cam02", "cam01"])

    def test_reorder_no_change(self):
        order = ["cam01", "cam02"]
        new_order = reorder_camera_order(order, "cam01", "cam01")
        self.assertEqual(new_order, order)

    def test_filter_alarm_events(self):
        events = [
            {"camera": "cam01", "level": "confirm", "time": "12:00:01"},
            {"camera": "cam02", "level": "warn", "time": "12:05:00"},
        ]
        filtered = filter_alarm_events(events, text="cam01", level="all")
        self.assertEqual(len(filtered), 1)
        filtered = filter_alarm_events(events, text="", level="confirm")
        self.assertEqual(len(filtered), 1)


if __name__ == "__main__":
    unittest.main()
