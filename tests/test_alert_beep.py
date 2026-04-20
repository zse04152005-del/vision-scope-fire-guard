import unittest
from core.alert_beep import AlertBeepState


class TestAlertBeepState(unittest.TestCase):
    def test_beep_sequence(self):
        state = AlertBeepState(beeps=2)
        self.assertTrue(state.next_beep())
        self.assertTrue(state.next_beep())
        self.assertIsNone(state.next_beep())

    def test_zero_beeps(self):
        state = AlertBeepState(beeps=0)
        self.assertIsNone(state.next_beep())


if __name__ == "__main__":
    unittest.main()
