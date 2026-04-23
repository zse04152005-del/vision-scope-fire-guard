"""Tests for ui.campus_map.CampusMapWidget."""

import json
import os
import sys
import tempfile
import time

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap

app = QApplication.instance() or QApplication(sys.argv)

from ui.campus_map import CampusMapWidget


@pytest.fixture
def widget():
    w = CampusMapWidget()
    w.resize(800, 600)
    return w


class TestCampusMapWidget:
    def test_initial_state(self, widget):
        assert widget._bg_pixmap is None
        assert widget._cam_positions == {}

    def test_set_cameras(self, widget):
        cams = [
            {"id": "cam01", "name": "A楼"},
            {"id": "cam02", "name": "B楼"},
        ]
        widget.set_cameras(cams)
        assert "cam01" in widget._cam_positions
        assert "cam02" in widget._cam_positions

    def test_set_cam_position(self, widget):
        widget.set_cameras([{"id": "cam01", "name": "Test"}])
        widget.set_cam_position("cam01", 0.3, 0.7)
        pos = widget._cam_positions["cam01"]
        assert abs(pos[0] - 0.3) < 0.01
        assert abs(pos[1] - 0.7) < 0.01

    def test_position_clamped(self, widget):
        widget.set_cam_position("cam01", -0.5, 1.5)
        pos = widget._cam_positions["cam01"]
        assert pos[0] >= 0.02
        assert pos[1] <= 0.98

    def test_trigger_alert(self, widget):
        widget.set_cameras([{"id": "cam01", "name": "Test"}])
        widget.trigger_alert("cam01")
        assert widget._alert_states["cam01"] > 0
        assert time.time() - widget._alert_states["cam01"] < 1.0

    def test_update_status(self, widget):
        widget.update_status("cam01", "ONLINE")
        assert widget._cam_status["cam01"] == "ONLINE"

    def test_paint_no_crash(self, widget):
        widget.set_cameras([
            {"id": "cam01", "name": "A楼"},
            {"id": "cam02", "name": "B楼"},
        ])
        widget.trigger_alert("cam01")
        widget.update_status("cam02", "ONLINE")
        widget.repaint()

    def test_save_and_load_layout(self, widget):
        widget.set_cameras([
            {"id": "cam01", "name": "A"},
            {"id": "cam02", "name": "B"},
        ])
        widget.set_cam_position("cam01", 0.25, 0.35)
        widget.set_cam_position("cam02", 0.75, 0.65)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            widget.save_layout(path)

            # Load into a new widget
            w2 = CampusMapWidget()
            w2.resize(800, 600)
            w2.set_cameras([{"id": "cam01", "name": "A"}, {"id": "cam02", "name": "B"}])
            w2.load_layout(path)
            pos1 = w2._cam_positions["cam01"]
            pos2 = w2._cam_positions["cam02"]
            assert abs(pos1[0] - 0.25) < 0.01
            assert abs(pos1[1] - 0.35) < 0.01
            assert abs(pos2[0] - 0.75) < 0.01
            assert abs(pos2[1] - 0.65) < 0.01
        finally:
            os.unlink(path)

    def test_get_positions(self, widget):
        widget.set_cameras([{"id": "cam01", "name": "X"}])
        widget.set_cam_position("cam01", 0.5, 0.5)
        positions = widget.get_positions()
        assert "cam01" in positions
        assert isinstance(positions["cam01"], tuple)
