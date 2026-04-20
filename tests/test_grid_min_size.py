import unittest
from PyQt6.QtCore import QSize
from ui.components import compute_grid_min_size


class TestGridMinSize(unittest.TestCase):
    def test_compute_grid_min_size(self):
        size = compute_grid_min_size(tile_w=200, tile_h=150, rows=3, cols=4, spacing=6)
        self.assertEqual(size, QSize(200 * 4 + 6 * 3, 150 * 3 + 6 * 2))


if __name__ == "__main__":
    unittest.main()
