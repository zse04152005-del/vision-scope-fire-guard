import unittest

import numpy as np

from core.heatmap_accumulator import HeatmapAccumulator


class MockBox:
    def __init__(self, x1, y1, x2, y2):
        self.xyxy = [np.array([x1, y1, x2, y2], dtype=np.float32)]


class TestHeatmapAccumulator(unittest.TestCase):
    def test_update_accumulates(self):
        ha = HeatmapAccumulator(map_w=80, map_h=60, decay=1.0)
        box = MockBox(0, 0, 320, 240)
        ha.update("cam01", [box], 640, 480)
        density = ha.get_density("cam01")
        self.assertIsNotNone(density)
        self.assertGreater(density.sum(), 0)

    def test_decay_reduces_values(self):
        ha = HeatmapAccumulator(map_w=80, map_h=60, decay=0.5)
        box = MockBox(0, 0, 640, 480)
        ha.update("cam01", [box], 640, 480)
        val_after_first = ha.get_density("cam01").sum()
        # Second update with no boxes — only decay
        ha.update("cam01", [], 640, 480)
        val_after_decay = ha.get_density("cam01").sum()
        self.assertLess(val_after_decay, val_after_first)

    def test_get_overlay_returns_correct_shape(self):
        ha = HeatmapAccumulator(map_w=80, map_h=60)
        box = MockBox(100, 100, 300, 300)
        ha.update("cam01", [box], 640, 480)
        overlay = ha.get_overlay("cam01", 640, 480)
        self.assertIsNotNone(overlay)
        self.assertEqual(overlay.shape, (480, 640, 3))

    def test_get_overlay_empty_returns_none(self):
        ha = HeatmapAccumulator()
        overlay = ha.get_overlay("cam99", 640, 480)
        self.assertIsNone(overlay)

    def test_reset_clears_map(self):
        ha = HeatmapAccumulator(decay=1.0)
        box = MockBox(0, 0, 320, 240)
        ha.update("cam01", [box], 640, 480)
        ha.reset("cam01")
        self.assertEqual(ha.get_density("cam01").sum(), 0.0)


if __name__ == "__main__":
    unittest.main()
