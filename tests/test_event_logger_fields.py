import csv
import os
import tempfile
import unittest

from core.event_logger import FIELDNAMES, write_event


class TestEventLoggerFields(unittest.TestCase):
    def test_field_order_stable_across_writes(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.csv")
            write_event(path, {"camera": "cam01", "level": "confirm", "ts": 1.0, "time": "00:00:01"})
            write_event(path, {"ts": 2.0, "camera": "cam02", "level": "warn"})
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                rows = list(reader)
            self.assertEqual(header[: len(FIELDNAMES)], FIELDNAMES)
            self.assertEqual(rows[0][header.index("camera")], "cam01")
            self.assertEqual(rows[1][header.index("camera")], "cam02")


if __name__ == "__main__":
    unittest.main()
