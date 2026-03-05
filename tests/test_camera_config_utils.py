import json
import tempfile
import unittest
from camera_config_utils import normalize_source, save_cameras


class TestCameraConfigUtils(unittest.TestCase):
    def test_normalize_source_digits(self):
        self.assertEqual(normalize_source("0"), 0)
        self.assertEqual(normalize_source(" 2 "), 2)

    def test_normalize_source_rtsp(self):
        src = "rtsp://user:pass@1.2.3.4:554/xxx"
        self.assertEqual(normalize_source(src), src)

    def test_save_cameras_updates_config(self):
        with tempfile.TemporaryDirectory() as d:
            path = f"{d}/config.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"cameras": []}, f)
            cams = [
                {"id": "cam01", "name": "USB-0", "source": 0},
                {"id": "cam02", "name": "RTSP-1", "source": "rtsp://x"},
            ]
            save_cameras(path, cams)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(len(data["cameras"]), 2)
            self.assertEqual(data["cameras"][0]["id"], "cam01")


if __name__ == "__main__":
    unittest.main()
