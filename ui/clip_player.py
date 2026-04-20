"""告警录像回放对话框 — 加载 .avi 片段并逐帧播放。"""

from PyQt6.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap


class ClipPlayerDialog(QDialog):
    """简易视频回放器，加载短录像片段并提供 播放/暂停/拖动 控制。"""

    def __init__(self, clip_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("告警录像回放")
        self.resize(680, 520)

        self.frames: list[QPixmap] = []
        self.idx = 0
        self._load_frames(clip_path)

        # --- UI ---
        self.label = QLabel("无录像帧")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumSize(320, 240)
        self.label.setStyleSheet("background-color: #000;")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, max(0, len(self.frames) - 1))
        self.slider.valueChanged.connect(self._on_seek)

        self.btn_play = QPushButton("▶ 播放")
        self.btn_play.setFixedWidth(90)
        self.btn_play.clicked.connect(self._toggle_play)

        self.lbl_info = QLabel(self._info_text())
        self.lbl_info.setFixedWidth(80)

        controls = QHBoxLayout()
        controls.addWidget(self.btn_play)
        controls.addWidget(self.slider, stretch=1)
        controls.addWidget(self.lbl_info)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label, stretch=1)
        layout.addLayout(controls)

        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 / max(1, self.fps)))
        self.timer.timeout.connect(self._next_frame)

        if self.frames:
            self._show_frame(0)

    # ---- internal ----

    def _load_frames(self, path: str):
        try:
            import cv2
            cap = cv2.VideoCapture(path)
            self.fps = cap.get(cv2.CAP_PROP_FPS) or 5
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
                self.frames.append(QPixmap.fromImage(qimg))
            cap.release()
        except Exception:
            self.fps = 5

    def _info_text(self):
        return f"{self.idx + 1}/{len(self.frames)}" if self.frames else "0/0"

    def _show_frame(self, idx: int):
        if 0 <= idx < len(self.frames):
            self.idx = idx
            scaled = self.frames[idx].scaled(
                self.label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.label.setPixmap(scaled)
            self.lbl_info.setText(self._info_text())
            self.slider.blockSignals(True)
            self.slider.setValue(idx)
            self.slider.blockSignals(False)

    def _next_frame(self):
        nxt = self.idx + 1
        if nxt >= len(self.frames):
            self.timer.stop()
            self.btn_play.setText("▶ 播放")
            return
        self._show_frame(nxt)

    def _on_seek(self, val: int):
        self._show_frame(val)

    def _toggle_play(self):
        if self.timer.isActive():
            self.timer.stop()
            self.btn_play.setText("▶ 播放")
        else:
            if not self.frames:
                return
            if self.idx >= len(self.frames) - 1:
                self.idx = 0
            self.timer.start()
            self.btn_play.setText("‖ 暂停")
