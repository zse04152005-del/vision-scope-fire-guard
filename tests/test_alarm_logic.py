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


    def test_continuous_hits_trigger_once(self):
        now = time.time()
        tracker = AlarmTracker(hit_threshold=3, cooldown_seconds=10)
        events = [tracker.update("cam01", True, now + i * 0.1) for i in range(10)]
        triggered = [e for e in events if e is not None]
        self.assertEqual(len(triggered), 1)

    def test_reset_on_miss_allows_retrigger(self):
        now = time.time()
        tracker = AlarmTracker(hit_threshold=2, cooldown_seconds=0)
        tracker.update("cam01", True, now)
        ev1 = tracker.update("cam01", True, now + 0.1)
        self.assertIsNotNone(ev1)
        tracker.update("cam01", False, now + 0.2)
        tracker.update("cam01", True, now + 0.3)
        ev2 = tracker.update("cam01", True, now + 0.4)
        self.assertIsNotNone(ev2)


if __name__ == "__main__":
    unittest.main()
