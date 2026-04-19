import os
import unittest

from camera_config_utils import normalize_source


class TestEnvExpand(unittest.TestCase):
    def test_expand_env_var(self):
        os.environ["TEST_RTSP_URL"] = "rtsp://user:pass@10.0.0.1/stream"
        result = normalize_source("${TEST_RTSP_URL}")
        self.assertEqual(result, "rtsp://user:pass@10.0.0.1/stream")
        del os.environ["TEST_RTSP_URL"]

    def test_missing_env_var_kept_as_is(self):
        result = normalize_source("${NONEXISTENT_VAR_12345}")
        self.assertEqual(result, "${NONEXISTENT_VAR_12345}")

    def test_no_placeholder_unchanged(self):
        result = normalize_source("rtsp://host/stream")
        self.assertEqual(result, "rtsp://host/stream")

    def test_int_source_unchanged(self):
        self.assertEqual(normalize_source(0), 0)


if __name__ == "__main__":
    unittest.main()
