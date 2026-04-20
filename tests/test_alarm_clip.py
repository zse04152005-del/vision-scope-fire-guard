import os
import tempfile
import unittest

import numpy as np

from core.alarm_clip import save_clip


class TestAlarmClip(unittest.TestCase):
    def test_save_clip_creates_file(self):
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(10)]
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test_clip.avi")
            result = save_clip(path, frames, fps=5.0)
            self.assertIsNotNone(result)
            self.assertTrue(os.path.exists(result))
            self.assertGreater(os.path.getsize(result), 0)

    def test_save_clip_empty_returns_none(self):
        result = save_clip("/tmp/empty.avi", [], fps=5.0)
        self.assertIsNone(result)

    def test_save_clip_auto_avi_extension(self):
        frames = [np.zeros((240, 320, 3), dtype=np.uint8) for _ in range(5)]
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "test.mp4")  # wrong ext
            result = save_clip(path, frames, fps=5.0)
            self.assertIsNotNone(result)
            self.assertTrue(result.endswith(".avi"))


if __name__ == "__main__":
    unittest.main()
