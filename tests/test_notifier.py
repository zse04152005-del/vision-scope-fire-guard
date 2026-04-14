import unittest
from unittest.mock import patch

from notifier import AlarmNotifier, build_alarm_text


class TestNotifier(unittest.TestCase):
    def test_disabled_when_no_urls(self):
        n = AlarmNotifier({})
        self.assertFalse(n.enabled())
        n.notify({"camera": "cam01"})  # 不应抛异常

    def test_build_alarm_text_contains_fields(self):
        text = build_alarm_text({"time": "12:00:00", "camera": "cam01", "level": "confirm"})
        self.assertIn("cam01", text)
        self.assertIn("confirm", text)

    def test_notify_dispatches_to_both(self):
        n = AlarmNotifier({"dingtalk_url": "https://d/x", "wecom_url": "https://w/y"})
        self.assertTrue(n.enabled())
        with patch("notifier._fire_and_forget") as mock_send:
            n.notify({"time": "t", "camera": "c", "level": "confirm"})
            self.assertEqual(mock_send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
