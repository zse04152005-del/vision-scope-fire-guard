import json
import os
import tempfile
import unittest

from config_loader import DEFAULT_CONFIG, load_config


class TestConfigLoaderDefaults(unittest.TestCase):
    def test_missing_file_returns_defaults(self):
        cfg = load_config("/nonexistent/path/to/config.json")
        self.assertEqual(cfg["grid_cols"], DEFAULT_CONFIG["grid_cols"])
        self.assertEqual(cfg["alarm"]["hit_threshold"], 3)

    def test_partial_user_config_merges_with_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cfg.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"alarm": {"hit_threshold": 7}}, f)
            cfg = load_config(path)
            self.assertEqual(cfg["alarm"]["hit_threshold"], 7)
            self.assertEqual(cfg["alarm"]["cooldown_seconds"], 10)
            self.assertEqual(cfg["model_path"], "best.pt")

    def test_invalid_json_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "bad.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not valid json")
            cfg = load_config(path)
            self.assertEqual(cfg["grid_cols"], DEFAULT_CONFIG["grid_cols"])


if __name__ == "__main__":
    unittest.main()
