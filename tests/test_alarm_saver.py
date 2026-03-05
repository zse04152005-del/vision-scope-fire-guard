import os
import unittest
from alarm_saver import build_alarm_paths


class TestAlarmSaver(unittest.TestCase):
    def test_build_alarm_paths(self):
        orig_path, ann_path = build_alarm_paths("results/alarms", "cam01", 0)
        self.assertTrue(orig_path.endswith(os.path.join("results", "alarms", "cam01_19700101_000000_orig.jpg")))
        self.assertTrue(ann_path.endswith(os.path.join("results", "alarms", "cam01_19700101_000000_annotated.jpg")))


if __name__ == "__main__":
    unittest.main()
