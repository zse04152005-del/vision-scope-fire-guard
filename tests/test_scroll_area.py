import unittest
from PyQt6.QtWidgets import QApplication, QLabel, QScrollArea
from ui.components import build_scroll_area


class TestScrollArea(unittest.TestCase):
    def test_build_scroll_area_wraps_widget(self):
        app = QApplication.instance() or QApplication([])
        label = QLabel("test")
        scroll = build_scroll_area(label)
        self.assertIsInstance(scroll, QScrollArea)
        self.assertIs(scroll.widget(), label)


if __name__ == "__main__":
    unittest.main()
