import unittest
from capture_worker import next_inference_time


class TestCaptureWorker(unittest.TestCase):
    def test_inference_interval(self):
        t0 = 0.0
        self.assertEqual(next_inference_time(t0, 0.2), 0.2)


if __name__ == "__main__":
    unittest.main()
