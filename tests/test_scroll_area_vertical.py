import unittest
from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtCore import Qt
from ui.components import build_scroll_area


class TestScrollAreaVertical(unittest.TestCase):
    def test_build_scroll_area_vertical_always_on(self):
        app = QApplication.instance() or QApplication([])
        label = QLabel("test")
        scroll = build_scroll_area(label, always_show_vertical=True)
        self.assertEqual(scroll.verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOn)


if __name__ == "__main__":
    unittest.main()
