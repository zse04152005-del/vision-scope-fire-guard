import unittest
from ui.components import compute_available_grid_width


class TestGridAvailableWidth(unittest.TestCase):
    def test_available_width(self):
        width = compute_available_grid_width(window_width=1200, right_width=320, padding=80)
        self.assertEqual(width, 800)


if __name__ == "__main__":
    unittest.main()
