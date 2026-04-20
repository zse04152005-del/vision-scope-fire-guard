import csv
import os
import tempfile
import unittest

from core.alarm_exporter import EXPORT_FIELDS, export_alarm_events_csv


class TestAlarmExporter(unittest.TestCase):
    def test_export_writes_header_and_rows(self):
        events = [
            {"time": "12:00:01", "ts": 1.0, "camera": "cam01", "level": "confirm", "status": "pending"},
            {"time": "12:00:02", "ts": 2.0, "camera": "cam02", "level": "warn", "status": "pending"},
        ]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.csv")
            n = export_alarm_events_csv(path, events)
            self.assertEqual(n, 2)
            with open(path, "r", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], EXPORT_FIELDS)
            self.assertEqual(rows[1][rows[0].index("camera")], "cam01")

    def test_export_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.csv")
            n = export_alarm_events_csv(path, [])
            self.assertEqual(n, 0)
            self.assertTrue(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
