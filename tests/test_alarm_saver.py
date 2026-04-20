import os
import time
import unittest
from core.alarm_saver import build_alarm_paths


class TestAlarmSaver(unittest.TestCase):
    def test_build_alarm_paths(self):
        ts = 0
        expected_ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(ts))
        orig_path, ann_path = build_alarm_paths("results/alarms", "cam01", ts)
        self.assertTrue(orig_path.endswith(f"cam01_{expected_ts}_orig.jpg"))
        self.assertTrue(ann_path.endswith(f"cam01_{expected_ts}_annotated.jpg"))

    def test_paths_use_localtime(self):
        ts = 1700000000
        expected_ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(ts))
        orig, _ = build_alarm_paths("out", "cam02", ts)
        self.assertIn(expected_ts, orig)


if __name__ == "__main__":
    unittest.main()
