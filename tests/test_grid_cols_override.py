import unittest
from ui.components import resolve_grid_cols


class TestGridColsOverride(unittest.TestCase):
    def test_override_cols(self):
        cols = resolve_grid_cols(config_cols=3, available_width=100, tile_w=240, spacing=6, max_cols=4)
        self.assertEqual(cols, 3)

    def test_fallback_to_auto(self):
        cols = resolve_grid_cols(config_cols=None, available_width=800, tile_w=240, spacing=6, max_cols=4)
        self.assertEqual(cols, 3)


if __name__ == "__main__":
    unittest.main()
