# Multi-Camera Dashboard + Alarm Center Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the current single-camera PyQt6 app into a 12-camera adaptive dashboard with a unified alarm center and faster alerting (1–2s).

**Architecture:** Split the system into modular services in the same project root: config loader, alarm logic, capture/inference workers, and UI grid. Use a single shared YOLO model with a global lock to avoid multi-instance GPU overhead; each camera worker reads latest frames and performs inference at a target interval.

**Tech Stack:** Python, PyQt6, OpenCV, Ultralytics YOLOv8, unittest (std lib)

---

### Task 1: Add config model + loader (JSON)

**Files:**
- Create: `config.json`
- Create: `config_loader.py`
- Create: `tests/fixtures/sample_config.json`
- Test: `tests/test_config_loader.py`

**Step 1: Write the failing test**

```python
import json
import unittest
from config_loader import load_config

class TestConfigLoader(unittest.TestCase):
    def test_load_config_reads_cameras(self):
        cfg = load_config("tests/fixtures/sample_config.json")
        self.assertEqual(len(cfg["cameras"]), 2)
        self.assertEqual(cfg["cameras"][0]["id"], "cam01")

if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_config_loader.py -v`
Expected: FAIL (ImportError: config_loader not found)

**Step 3: Write minimal implementation**

```python
import json

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_config_loader.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add config.json config_loader.py tests/test_config_loader.py
# skip commit if repo missing
```

---

### Task 2: Alarm logic (sliding window + cooldown)

**Files:**
- Create: `alarm_logic.py`
- Test: `tests/test_alarm_logic.py`

**Step 1: Write the failing test**

```python
import time
import unittest
from alarm_logic import AlarmTracker

class TestAlarmTracker(unittest.TestCase):
    def test_triggers_after_consecutive_hits(self):
        tracker = AlarmTracker(hit_threshold=3, cooldown_seconds=5)
        for _ in range(2):
            self.assertIsNone(tracker.update("cam01", True, time.time()))
        event = tracker.update("cam01", True, time.time())
        self.assertIsNotNone(event)
        self.assertEqual(event["level"], "confirm")

    def test_cooldown_blocks_repeated_alerts(self):
        now = time.time()
        tracker = AlarmTracker(hit_threshold=2, cooldown_seconds=10)
        tracker.update("cam01", True, now)
        event1 = tracker.update("cam01", True, now)
        self.assertIsNotNone(event1)
        event2 = tracker.update("cam01", True, now + 1)
        self.assertIsNone(event2)

if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_alarm_logic.py -v`
Expected: FAIL (ImportError: alarm_logic not found)

**Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class AlarmState:
    hits: int = 0
    last_alert_ts: float = 0.0

class AlarmTracker:
    def __init__(self, hit_threshold: int, cooldown_seconds: int):
        self.hit_threshold = hit_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state: Dict[str, AlarmState] = {}

    def update(self, cam_id: str, hit: bool, ts: float):
        st = self.state.setdefault(cam_id, AlarmState())
        st.hits = st.hits + 1 if hit else 0
        if st.hits >= self.hit_threshold:
            if ts - st.last_alert_ts >= self.cooldown_seconds:
                st.last_alert_ts = ts
                return {"camera": cam_id, "level": "confirm", "ts": ts}
        return None
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_alarm_logic.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add alarm_logic.py tests/test_alarm_logic.py
# skip commit if repo missing
```

---

### Task 3: Build multi-camera UI skeleton (grid + alarm center)

**Files:**
- Modify: `fire_detection_system.py`
- Create: `ui_components.py`
- Test: `tests/test_ui_layout_stub.py`

**Step 1: Write the failing test**

```python
import unittest
from ui_components import build_grid_positions

class TestUILayout(unittest.TestCase):
    def test_grid_positions_12(self):
        positions = build_grid_positions(12, cols=4)
        self.assertEqual(len(positions), 12)
        self.assertEqual(positions[0], (0, 0))
        self.assertEqual(positions[11], (2, 3))

if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_ui_layout_stub.py -v`
Expected: FAIL (ImportError: ui_components not found)

**Step 3: Write minimal implementation**

```python
from typing import List, Tuple

def build_grid_positions(count: int, cols: int) -> List[Tuple[int, int]]:
    return [(i // cols, i % cols) for i in range(count)]
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_ui_layout_stub.py -v`
Expected: PASS

**Step 5: Implement UI skeleton**
- Add a `CameraTile` widget with video label + status + name
- Create a grid container with 12 tiles
- Add right-side alarm center list

**Step 6: Commit**

```bash
git add ui_components.py fire_detection_system.py tests/test_ui_layout_stub.py
# skip commit if repo missing
```

---

### Task 4: Integrate capture/inference workers (multi-camera)

**Files:**
- Modify: `fire_detection_system.py`
- Create: `capture_worker.py`

**Step 1: Write the failing test**

```python
import unittest
from capture_worker import next_inference_time

class TestCaptureWorker(unittest.TestCase):
    def test_inference_interval(self):
        t0 = 0.0
        self.assertEqual(next_inference_time(t0, 0.2), 0.2)

if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_capture_worker.py -v`
Expected: FAIL (ImportError: capture_worker not found)

**Step 3: Write minimal implementation**

```python
def next_inference_time(last_ts: float, interval_s: float) -> float:
    return last_ts + interval_s
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_capture_worker.py -v`
Expected: PASS

**Step 5: Implement worker**
- Each worker reads frames, uses shared model + lock
- Emits latest QImage + max conf + class names
- Sends detection hits to AlarmTracker

**Step 6: Commit**

```bash
git add capture_worker.py fire_detection_system.py tests/test_capture_worker.py
# skip commit if repo missing
```

---

### Task 5: Event logging + notification hooks

**Files:**
- Create: `event_logger.py`
- Modify: `fire_detection_system.py`
- Test: `tests/test_event_logger.py`

**Step 1: Write the failing test**

```python
import os
import tempfile
import unittest
from event_logger import write_event

class TestEventLogger(unittest.TestCase):
    def test_write_event_creates_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "events.csv")
            write_event(path, {"camera": "cam01", "level": "confirm", "ts": 0.0})
            self.assertTrue(os.path.exists(path))

if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests/test_event_logger.py -v`
Expected: FAIL (ImportError: event_logger not found)

**Step 3: Write minimal implementation**

```python
import csv
import os

def write_event(path: str, event: dict) -> None:
    file_exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=sorted(event.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(event)
```

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests/test_event_logger.py -v`
Expected: PASS

**Step 5: Wire up notifications**
- Add placeholder function for DingTalk/WeChat webhook
- Trigger on “confirm” events only

**Step 6: Commit**

```bash
git add event_logger.py fire_detection_system.py tests/test_event_logger.py
# skip commit if repo missing
```

---

### Task 6: Performance + stability hardening

**Files:**
- Modify: `fire_detection_system.py`
- Modify: `capture_worker.py`

**Steps:**
1) Add RTSP reconnect loop with timeout
2) Add per-camera FPS limiter
3) Add UI indicator for offline cameras
4) Add global toggle to pause all workers

---

## Notes
- This project is not a git repo; commits are optional.
- Use relative paths for model and output folders; avoid absolute desktop paths.
