import unittest
from alert_flash import AlertFlashState


class TestAlertFlashState(unittest.TestCase):
    def test_flash_sequence(self):
        state = AlertFlashState(cycles=2)
        self.assertEqual(state.next_color(), "#ff3b30")
        self.assertEqual(state.next_color(), "transparent")
        self.assertIsNone(state.next_color())

    def test_zero_cycles(self):
        state = AlertFlashState(cycles=0)
        self.assertIsNone(state.next_color())


if __name__ == "__main__":
    unittest.main()
