"""Tests for ui.timeline_widget.TimelineWidget."""

import time
import sys
import pytest

from PyQt6.QtWidgets import QApplication

# Ensure QApplication exists for widget tests
app = QApplication.instance() or QApplication(sys.argv)

from ui.timeline_widget import TimelineWidget


@pytest.fixture
def widget():
    w = TimelineWidget()
    w.resize(800, 80)
    return w


class TestTimelineWidget:
    def test_initial_state(self, widget):
        assert widget._events == []
        assert widget._day_start > 0

    def test_set_events(self, widget):
        events = [
            {"ts": time.time() - 3600, "level": "confirm", "camera": "cam1"},
            {"ts": time.time() - 1800, "level": "warn", "camera": "cam2"},
        ]
        widget.set_events(events)
        assert widget._events == events

    def test_ts_to_x_boundaries(self, widget):
        # Start of day should map near left margin
        x_start = widget._ts_to_x(widget._day_start)
        assert x_start == 30  # margin

        # End of day should map near right edge
        x_end = widget._ts_to_x(widget._day_start + 86400)
        assert x_end == widget.width() - 30

    def test_x_to_ts_roundtrip(self, widget):
        ts = widget._day_start + 43200  # noon
        x = widget._ts_to_x(ts)
        ts_back = widget._x_to_ts(x)
        assert abs(ts_back - ts) < 200  # within a few minutes tolerance

    def test_paint_no_crash(self, widget):
        """Painting with events should not raise."""
        events = [
            {"ts": time.time() - 100, "level": "confirm"},
            {"ts": time.time() - 50, "level": "spreading"},
            {"ts": time.time() - 10, "level": "warn"},
        ]
        widget.set_events(events)
        widget.repaint()  # should not crash
