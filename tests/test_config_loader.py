import unittest
from utils.config_loader import load_config


class TestConfigLoader(unittest.TestCase):
    def test_load_config_reads_cameras(self):
        cfg = load_config("tests/fixtures/sample_config.json")
        self.assertEqual(len(cfg["cameras"]), 2)
        self.assertEqual(cfg["cameras"][0]["id"], "cam01")


if __name__ == "__main__":
    unittest.main()
