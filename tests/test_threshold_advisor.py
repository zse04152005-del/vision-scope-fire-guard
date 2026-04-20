import time
import unittest

from core.threshold_advisor import ThresholdAdvisor


class TestThresholdAdvisor(unittest.TestCase):
    def test_no_events_keep(self):
        advisor = ThresholdAdvisor(0.5)
        cameras = [{"id": "cam01"}]
        result = advisor.analyze([], cameras)
        self.assertEqual(result[0]["suggestion"], "keep")

    def test_high_freq_suggest_raise(self):
        advisor = ThresholdAdvisor(0.5)
        ts = time.time()
        # 60 events in ~60 seconds = 60/hr >> HIGH_FREQ
        events = [{"camera": "cam01", "ts": ts + i, "max_conf": 0.6} for i in range(60)]
        cameras = [{"id": "cam01"}]
        result = advisor.analyze(events, cameras)
        self.assertEqual(result[0]["suggestion"], "raise")
        self.assertGreater(result[0]["recommended"], 0.5)

    def test_high_conf_low_freq_suggest_lower(self):
        advisor = ThresholdAdvisor(0.5)
        ts = time.time()
        # 3 events in 2 hours with high confidence
        events = [
            {"camera": "cam01", "ts": ts, "max_conf": 0.92},
            {"camera": "cam01", "ts": ts + 3600, "max_conf": 0.88},
            {"camera": "cam01", "ts": ts + 7200, "max_conf": 0.95},
        ]
        cameras = [{"id": "cam01"}]
        result = advisor.analyze(events, cameras)
        self.assertEqual(result[0]["suggestion"], "lower")
        self.assertLess(result[0]["recommended"], 0.5)

    def test_near_edge_suggest_raise(self):
        advisor = ThresholdAdvisor(0.5)
        ts = time.time()
        # Most alarms just above threshold (0.50-0.55)
        events = [
            {"camera": "cam01", "ts": ts + i * 600, "max_conf": 0.52}
            for i in range(5)
        ]
        cameras = [{"id": "cam01"}]
        result = advisor.analyze(events, cameras)
        self.assertEqual(result[0]["suggestion"], "raise")


if __name__ == "__main__":
    unittest.main()
