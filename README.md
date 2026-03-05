# VisionScope Fire Guard

A multi-camera, real-time fire & smoke detection system based on an improved YOLOv8 model. The project provides a desktop monitoring dashboard, alarm center, and event logging with screenshots.

## Features
- 12-camera dashboard with drag-to-reorder tiles (order persists)
- Real-time fire/smoke detection using YOLOv8
- Alarm center with search/filter and detail view
- Alarm screenshots saved as **original** + **annotated** images
- Visual alarm: flashing border + continuous beep
- Camera manager (add/remove/test/save sources)
- Fullscreen toggle (F11)

## Requirements
- Python 3.10+ (recommended)
- OS: macOS / Windows / Linux

## Installation
Create environment (Conda recommended):
```
conda create -n fireguard python=3.10 -y
conda activate fireguard
```

Install dependencies:
```
python -m pip install ultralytics opencv-python PyQt6
```

If PyTorch is missing:
```
python -m pip install torch
```

## Run
From project directory:
```
python fire_detection_system.py
```

## Configuration
Edit `config.json`:
- `model_path`: model weights (default `best.pt`)
- `output_dir`: output directory (default `results`)
- `alarm.hit_threshold`: consecutive hits to trigger alarm
- `alarm.cooldown_seconds`: cooldown per camera
- `alarm.conf_threshold`: confidence threshold
- `alarm.interval_s`: inference interval per camera (seconds)
- `grid_cols`: fixed grid columns (recommended 3 for 3x4 layout)

### Add Cameras
In `config.json`, update the `cameras` array.

USB camera:
```json
{"id": "cam01", "name": "USB-0", "source": 0}
```

RTSP camera:
```json
{"id": "cam01", "name": "Lab-01", "source": "rtsp://user:pass@192.168.1.20:554/xxx"}
```

After editing, restart the app.

## Outputs
- Alarm images: `results/alarms/`
- Event log: `results/events.csv`

## Controls
- **F11**: Fullscreen toggle
- **Double-click** a camera tile: Open zoom window
- **Drag & drop** tiles: Reorder (saved to `config.json`)

## Notes
- On macOS (CPU-only), inference is slower. For real-time performance, use a Windows machine with NVIDIA GPU.
- `results/` is excluded from Git by default.

## License
For academic use.
