import os
import tempfile
import unittest
from event_logger import write_event


class TestEventLogger(unittest.TestCase):
    def test_write_event_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.csv")
            write_event(path, {"camera": "cam01", "level": "confirm", "ts": 0.0})
            self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
