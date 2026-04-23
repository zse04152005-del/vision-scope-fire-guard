"""Tests for core.roi_manager.ROIManager."""

import json
import os
import tempfile
from unittest.mock import MagicMock

import numpy as np
import pytest

from core.roi_manager import ROIManager


@pytest.fixture
def roi_mgr():
    return ROIManager()


class TestROIManager:
    def test_set_and_get_roi(self, roi_mgr):
        poly = [[(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]]
        roi_mgr.set_roi("cam01", poly)
        assert roi_mgr.get_roi("cam01") == poly
        assert roi_mgr.has_roi("cam01")

    def test_no_roi_returns_empty(self, roi_mgr):
        assert roi_mgr.get_roi("cam99") == []
        assert not roi_mgr.has_roi("cam99")

    def test_clear_roi(self, roi_mgr):
        roi_mgr.set_roi("cam01", [[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]])
        roi_mgr.clear_roi("cam01")
        assert not roi_mgr.has_roi("cam01")

    def test_filter_boxes_no_roi_returns_all(self, roi_mgr):
        boxes = [MagicMock() for _ in range(3)]
        result = roi_mgr.filter_boxes("cam01", boxes, 640, 480)
        assert result == [0, 1, 2]

    def test_filter_boxes_center_inside(self, roi_mgr):
        # ROI: left half of image (x: 0~0.5, y: 0~1)
        roi_mgr.set_roi("cam01", [[(0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)]])

        # Box 1: center at (160, 240) — inside left half
        box1 = MagicMock()
        box1.xyxy = [np.array([100, 200, 220, 280])]

        # Box 2: center at (480, 240) — outside left half
        box2 = MagicMock()
        box2.xyxy = [np.array([400, 200, 560, 280])]

        kept = roi_mgr.filter_boxes("cam01", [box1, box2], 640, 480)
        assert kept == [0]  # only box1 is inside

    def test_filter_boxes_center_outside(self, roi_mgr):
        # ROI: small region top-left corner
        roi_mgr.set_roi("cam01", [[(0.0, 0.0), (0.1, 0.0), (0.1, 0.1), (0.0, 0.1)]])

        # Box center at image center — outside
        box = MagicMock()
        box.xyxy = [np.array([280, 200, 360, 280])]

        kept = roi_mgr.filter_boxes("cam01", [box], 640, 480)
        assert kept == []

    def test_save_and_load(self, roi_mgr):
        roi_mgr.set_roi("cam01", [[(0.1, 0.2), (0.3, 0.4), (0.5, 0.6)]])
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            roi_mgr.save(path)
            new_mgr = ROIManager(config_path=path)
            assert new_mgr.has_roi("cam01")
            assert len(new_mgr.get_roi("cam01")) == 1
            assert len(new_mgr.get_roi("cam01")[0]) == 3
        finally:
            os.unlink(path)

    def test_draw_overlay_no_roi(self, roi_mgr):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = roi_mgr.draw_overlay(frame, "cam01")
        np.testing.assert_array_equal(result, frame)

    def test_draw_overlay_with_roi(self, roi_mgr):
        roi_mgr.set_roi("cam01", [[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)]])
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = roi_mgr.draw_overlay(frame, "cam01")
        assert result.shape == frame.shape
        # Overlay should have added some non-zero pixels
        assert result.sum() > 0
