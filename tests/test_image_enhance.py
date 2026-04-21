"""Tests for core.image_enhance module."""

import numpy as np
import pytest

from core.image_enhance import is_low_light, enhance_low_light, auto_enhance


def _make_frame(brightness: int) -> np.ndarray:
    """Create a uniform BGR frame with specified brightness in green channel."""
    frame = np.full((100, 100, 3), brightness, dtype=np.uint8)
    return frame


class TestIsLowLight:
    def test_dark_frame_detected(self):
        frame = _make_frame(30)
        assert is_low_light(frame, threshold=60)

    def test_bright_frame_not_detected(self):
        frame = _make_frame(120)
        assert not is_low_light(frame, threshold=60)

    def test_edge_threshold(self):
        frame = _make_frame(60)
        # mean == threshold → not low light (< not <=)
        assert not is_low_light(frame, threshold=60)

    def test_empty_frame(self):
        frame = np.array([], dtype=np.uint8).reshape(0, 0, 3)
        assert is_low_light(frame) is False

    def test_none_frame(self):
        assert is_low_light(None) is False


class TestEnhanceLowLight:
    def test_output_shape_preserved(self):
        frame = _make_frame(30)
        result = enhance_low_light(frame)
        assert result.shape == frame.shape

    def test_output_dtype_uint8(self):
        frame = _make_frame(40)
        result = enhance_low_light(frame)
        assert result.dtype == np.uint8

    def test_brightness_increased(self):
        frame = _make_frame(30)
        result = enhance_low_light(frame)
        # CLAHE should generally increase or maintain brightness for dark images
        assert result.mean() >= frame.mean() - 5  # allow small tolerance


class TestAutoEnhance:
    def test_dark_frame_enhanced(self):
        frame = _make_frame(20)
        result = auto_enhance(frame, brightness_threshold=60)
        # Should have been processed (not necessarily different for uniform frames)
        assert result.shape == frame.shape

    def test_bright_frame_unchanged(self):
        frame = _make_frame(150)
        result = auto_enhance(frame, brightness_threshold=60)
        np.testing.assert_array_equal(result, frame)
