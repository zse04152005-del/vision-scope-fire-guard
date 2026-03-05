import time
import unittest
from alarm_logic import AlarmTracker


class TestAlarmTracker(unittest.TestCase):
    def test_triggers_after_consecutive_hits(self):
        tracker = AlarmTracker(hit_threshold=3, cooldown_seconds=5)
        for _ in range(2):
            self.assertIsNone(tracker.update("cam01", True, time.time()))
        event = tracker.update("cam01", True, time.time())
        self.assertIsNotNone(event)
        self.assertEqual(event["level"], "confirm")

    def test_cooldown_blocks_repeated_alerts(self):
        now = time.time()
        tracker = AlarmTracker(hit_threshold=2, cooldown_seconds=10)
        tracker.update("cam01", True, now)
        event1 = tracker.update("cam01", True, now)
        self.assertIsNotNone(event1)
        event2 = tracker.update("cam01", True, now + 1)
        self.assertIsNone(event2)


if __name__ == "__main__":
    unittest.main()
