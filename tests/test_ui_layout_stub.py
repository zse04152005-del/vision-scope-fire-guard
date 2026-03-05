import unittest
from ui_components import build_grid_positions


class TestUILayout(unittest.TestCase):
    def test_grid_positions_12(self):
        positions = build_grid_positions(12, cols=4)
        self.assertEqual(len(positions), 12)
        self.assertEqual(positions[0], (0, 0))
        self.assertEqual(positions[11], (2, 3))


if __name__ == "__main__":
    unittest.main()
