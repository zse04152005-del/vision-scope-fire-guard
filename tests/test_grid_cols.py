import unittest
from ui_components import compute_grid_cols


class TestGridCols(unittest.TestCase):
    def test_grid_cols_fits_width(self):
        cols = compute_grid_cols(available_width=800, tile_w=240, spacing=6, max_cols=4)
        self.assertEqual(cols, 3)

    def test_grid_cols_falls_back_to_one(self):
        cols = compute_grid_cols(available_width=100, tile_w=240, spacing=6, max_cols=4)
        self.assertEqual(cols, 1)


if __name__ == "__main__":
    unittest.main()
