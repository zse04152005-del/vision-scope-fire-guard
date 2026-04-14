import unittest

from ui_theme import DARK, LIGHT, build_qss, get_theme


class TestUiTheme(unittest.TestCase):
    def test_get_theme_defaults_to_dark(self):
        self.assertEqual(get_theme(None).name, "dark")
        self.assertEqual(get_theme("unknown").name, "dark")

    def test_get_theme_case_insensitive(self):
        self.assertEqual(get_theme("LIGHT").name, "light")
        self.assertEqual(get_theme("Dark").name, "dark")

    def test_build_qss_contains_theme_colors(self):
        qss = build_qss(DARK)
        self.assertIn(DARK.bg, qss)
        self.assertIn(DARK.primary, qss)
        qss2 = build_qss(LIGHT)
        self.assertIn(LIGHT.bg, qss2)


if __name__ == "__main__":
    unittest.main()
