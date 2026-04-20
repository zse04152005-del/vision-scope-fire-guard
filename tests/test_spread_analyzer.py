import time
import unittest

import numpy as np

from core.spread_analyzer import SpreadAnalyzer, TREND_STABLE, TREND_GROWING, TREND_SPREADING


class MockBox:
    """Simulates an ultralytics Box with .xyxy attribute."""
    def __init__(self, x1, y1, x2, y2):
        self.xyxy = [np.array([x1, y1, x2, y2], dtype=np.float32)]
        self.conf = np.array([0.8])


class TestSpreadAnalyzer(unittest.TestCase):
    def test_no_detections_stable(self):
        sa = SpreadAnalyzer(window_size=10)
        for i in range(10):
            trend = sa.update("cam01", [], 640, 480, time.time() + i)
        self.assertEqual(trend, TREND_STABLE)

    def test_constant_area_stable(self):
        sa = SpreadAnalyzer(window_size=10)
        box = MockBox(0, 0, 100, 100)
        for i in range(10):
            trend = sa.update("cam01", [box], 640, 480, time.time() + i)
        self.assertEqual(trend, TREND_STABLE)

    def test_growing_area_detected(self):
        sa = SpreadAnalyzer(window_size=12, grow_ratio=1.3, spread_ratio=2.0)
        for i in range(12):
            side = 50 + i * 20  # growing from 50 to 270
            box = MockBox(0, 0, side, side)
            trend = sa.update("cam01", [box], 640, 480, time.time() + i)
        self.assertIn(trend, [TREND_GROWING, TREND_SPREADING])

    def test_rapid_spread_detected(self):
        sa = SpreadAnalyzer(window_size=9, spread_ratio=2.0)
        for i in range(9):
            side = 30 + i * 40  # rapid: 30 to 350
            box = MockBox(0, 0, side, side)
            trend = sa.update("cam01", [box], 640, 480, time.time() + i)
        self.assertEqual(trend, TREND_SPREADING)

    def test_get_chart_data(self):
        sa = SpreadAnalyzer(window_size=5)
        box = MockBox(0, 0, 100, 100)
        t0 = time.time()
        for i in range(5):
            sa.update("cam01", [box], 640, 480, t0 + i)
        data = sa.get_chart_data("cam01")
        self.assertEqual(len(data), 5)
        self.assertAlmostEqual(data[0][0], 0.0)


if __name__ == "__main__":
    unittest.main()
