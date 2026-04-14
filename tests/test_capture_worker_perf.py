import unittest
from unittest.mock import MagicMock

from capture_worker import CameraWorker


class TestCameraWorkerPerfParams(unittest.TestCase):
    def _make(self, **kwargs):
        defaults = dict(
            cam_id="cam01",
            source=0,
            model=MagicMock(),
            model_lock=MagicMock(),
            conf_threshold=0.5,
            interval_s=0.2,
        )
        defaults.update(kwargs)
        return CameraWorker(**defaults)

    def test_default_perf_params(self):
        w = self._make()
        self.assertEqual(w.infer_size, 0)
        self.assertEqual(w.heartbeat_timeout, 5.0)

    def test_custom_perf_params(self):
        w = self._make(infer_size=640, heartbeat_timeout=10.0)
        self.assertEqual(w.infer_size, 640)
        self.assertEqual(w.heartbeat_timeout, 10.0)

    def test_conf_threshold_threadsafe_accessor(self):
        w = self._make()
        w.conf_threshold = 0.7
        self.assertAlmostEqual(w.conf_threshold, 0.7)
        w.set_conf_threshold(0.3)
        self.assertAlmostEqual(w.conf_threshold, 0.3)


if __name__ == "__main__":
    unittest.main()
