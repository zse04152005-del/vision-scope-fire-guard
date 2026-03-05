import unittest
from PyQt6.QtWidgets import QApplication
from ui_components import CameraTile


class TestCameraTile(unittest.TestCase):
    def test_camera_tile_sets_name(self):
        app = QApplication.instance() or QApplication([])
        tile = CameraTile("Cam01")
        self.assertEqual(tile.name_label.text(), "Cam01")


if __name__ == "__main__":
    unittest.main()
