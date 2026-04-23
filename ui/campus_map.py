"""校园地图火情态势图 — 在平面图上显示摄像头位置和实时告警状态。"""

import json
import logging
import os
import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QToolTip, QDialog, QSizePolicy,
)
from PyQt6.QtCore import Qt, QPointF, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QPixmap, QMouseEvent,
    QPainterPath, QRadialGradient,
)

logger = logging.getLogger(__name__)


class CampusMapWidget(QWidget):
    """可交互的校园地图组件。

    功能：
    - 加载校园平面图作为底图
    - 拖拽放置摄像头图标到地图位置
    - 告警时对应位置脉冲闪烁
    - 点击摄像头图标 emit camera_clicked 信号
    """

    camera_clicked = pyqtSignal(str)  # cam_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self._bg_pixmap: QPixmap | None = None
        # cam_id -> (norm_x, norm_y) 归一化坐标
        self._cam_positions: dict[str, tuple[float, float]] = {}
        # cam_id -> camera info dict
        self._cam_info: dict[str, dict] = {}
        # cam_id -> alert state
        self._alert_states: dict[str, float] = {}  # cam_id -> alert_ts (0 = no alert)
        # cam_id -> status
        self._cam_status: dict[str, str] = {}

        # 拖拽状态
        self._dragging_cam: str | None = None
        self._drag_offset = QPointF()

        # 脉冲动画
        self._pulse_phase = 0
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(80)
        self._pulse_timer.timeout.connect(self._on_pulse)
        self._pulse_timer.start()

    def set_background(self, pixmap: QPixmap) -> None:
        self._bg_pixmap = pixmap
        self.update()

    def load_background(self, path: str) -> bool:
        pm = QPixmap(path)
        if pm.isNull():
            return False
        self._bg_pixmap = pm
        self.update()
        return True

    def set_cameras(self, cameras: list[dict]) -> None:
        """设置摄像头列表，未定位的会自动分配默认位置。"""
        for i, cam in enumerate(cameras):
            cam_id = cam.get("id", f"cam{i+1:02d}")
            self._cam_info[cam_id] = cam
            if cam_id not in self._cam_positions:
                # 默认沿中间均匀排列
                n = len(cameras)
                x = 0.15 + 0.7 * (i / max(1, n - 1)) if n > 1 else 0.5
                y = 0.5
                self._cam_positions[cam_id] = (x, y)
        self.update()

    def set_cam_position(self, cam_id: str, norm_x: float, norm_y: float) -> None:
        self._cam_positions[cam_id] = (
            max(0.02, min(0.98, norm_x)),
            max(0.02, min(0.98, norm_y)),
        )
        self.update()

    def get_positions(self) -> dict[str, tuple[float, float]]:
        return dict(self._cam_positions)

    def trigger_alert(self, cam_id: str) -> None:
        self._alert_states[cam_id] = time.time()

    def update_status(self, cam_id: str, status: str) -> None:
        self._cam_status[cam_id] = status
        self.update()

    def _on_pulse(self):
        self._pulse_phase = (self._pulse_phase + 1) % 30
        # 只在有告警时刷新
        now = time.time()
        has_active = any(
            now - ts < 10.0 for ts in self._alert_states.values() if ts > 0
        )
        if has_active:
            self.update()

    def _norm_to_pixel(self, nx: float, ny: float) -> QPointF:
        return QPointF(nx * self.width(), ny * self.height())

    def _pixel_to_norm(self, pos: QPointF) -> tuple[float, float]:
        return (
            max(0.02, min(0.98, pos.x() / max(1, self.width()))),
            max(0.02, min(0.98, pos.y() / max(1, self.height()))),
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # 背景
        if self._bg_pixmap and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(0, 0, scaled)
        else:
            # 无底图时绘制网格占位
            painter.fillRect(0, 0, w, h, QColor("#1e2028"))
            painter.setPen(QPen(QColor("#2a2f3a"), 1))
            for x in range(0, w, 40):
                painter.drawLine(x, 0, x, h)
            for y in range(0, h, 40):
                painter.drawLine(0, y, w, y)
            painter.setPen(QColor("#4b5563"))
            painter.setFont(QFont("Sans Serif", 10))
            painter.drawText(
                QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter,
                "点击「加载地图」导入校园平面图",
            )

        now = time.time()

        # 绘制摄像头
        for cam_id, (nx, ny) in self._cam_positions.items():
            pos = self._norm_to_pixel(nx, ny)
            status = self._cam_status.get(cam_id, "OFFLINE")
            alert_ts = self._alert_states.get(cam_id, 0)
            is_alerting = (alert_ts > 0 and now - alert_ts < 10.0)

            self._draw_camera_marker(painter, pos, cam_id, status, is_alerting)

        painter.end()

    def _draw_camera_marker(self, painter: QPainter, pos: QPointF,
                            cam_id: str, status: str, is_alerting: bool):
        x, y = pos.x(), pos.y()
        cam = self._cam_info.get(cam_id, {})
        name = cam.get("name", cam_id)

        # 告警脉冲光环
        if is_alerting:
            pulse = abs(self._pulse_phase - 15) / 15.0  # 0~1 oscillation
            radius = 20 + pulse * 16
            grad = QRadialGradient(x, y, radius)
            grad.setColorAt(0, QColor(220, 38, 38, int(180 * (1 - pulse * 0.5))))
            grad.setColorAt(1, QColor(220, 38, 38, 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPointF(x, y), radius, radius)

        # 摄像头图标（圆形）
        if is_alerting:
            fill = QColor("#dc2626")
            border = QColor("#fca5a5")
        elif status == "ONLINE":
            fill = QColor("#22c55e")
            border = QColor("#86efac")
        elif status == "RECONNECTING":
            fill = QColor("#f59e0b")
            border = QColor("#fcd34d")
        else:
            fill = QColor("#6b7280")
            border = QColor("#9ca3af")

        painter.setPen(QPen(border, 2))
        painter.setBrush(QBrush(fill))
        painter.drawEllipse(QPointF(x, y), 10, 10)

        # 摄像头图标内部（简易相机形状）
        painter.setPen(QPen(QColor("#ffffff"), 1.5))
        painter.drawRect(QRectF(x - 5, y - 3, 10, 6))
        painter.drawEllipse(QPointF(x, y), 2.5, 2.5)

        # 名称标签
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
        text_rect = QRectF(x - 40, y + 14, 80, 16)
        # 标签背景
        painter.setPen(Qt.PenStyle.NoPen)
        bg = QColor("#000000")
        bg.setAlpha(160)
        painter.setBrush(QBrush(bg))
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(name) + 8
        label_rect = QRectF(x - tw / 2, y + 13, tw, 16)
        painter.drawRoundedRect(label_rect, 3, 3)

        painter.setPen(QColor("#ffffff"))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, name)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            # 检查是否点击了某个摄像头
            for cam_id, (nx, ny) in self._cam_positions.items():
                cam_pos = self._norm_to_pixel(nx, ny)
                if (pos - cam_pos).manhattanLength() < 20:
                    self._dragging_cam = cam_id
                    self._drag_offset = pos - cam_pos
                    return
            # 没有点击到任何摄像头
            self._dragging_cam = None

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()

        if self._dragging_cam and (event.buttons() & Qt.MouseButton.LeftButton):
            new_pos = pos - self._drag_offset
            nx, ny = self._pixel_to_norm(new_pos)
            self._cam_positions[self._dragging_cam] = (nx, ny)
            self.update()
            return

        # Tooltip
        for cam_id, (nx, ny) in self._cam_positions.items():
            cam_pos = self._norm_to_pixel(nx, ny)
            if (pos - cam_pos).manhattanLength() < 20:
                cam = self._cam_info.get(cam_id, {})
                status = self._cam_status.get(cam_id, "OFFLINE")
                name = cam.get("name", cam_id)
                alert_ts = self._alert_states.get(cam_id, 0)
                alert_str = ""
                if alert_ts > 0 and time.time() - alert_ts < 10.0:
                    alert_str = " | 火警告警中!"
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"{name} ({cam_id})\n状态: {status}{alert_str}",
                )
                self.setCursor(Qt.CursorShape.OpenHandCursor)
                return

        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._dragging_cam:
                self._dragging_cam = None
            else:
                # 单击判定
                pos = event.position()
                for cam_id, (nx, ny) in self._cam_positions.items():
                    cam_pos = self._norm_to_pixel(nx, ny)
                    if (pos - cam_pos).manhattanLength() < 20:
                        self.camera_clicked.emit(cam_id)
                        return

    def save_layout(self, path: str) -> None:
        """保存摄像头地图布局。"""
        try:
            data = {
                "positions": {
                    k: list(v) for k, v in self._cam_positions.items()
                },
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("保存地图布局失败: %s", exc)

    def load_layout(self, path: str) -> None:
        """加载摄像头地图布局。"""
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            positions = data.get("positions", {})
            for cam_id, coords in positions.items():
                if isinstance(coords, (list, tuple)) and len(coords) == 2:
                    self._cam_positions[cam_id] = (float(coords[0]), float(coords[1]))
            self.update()
        except Exception as exc:
            logger.error("加载地图布局失败: %s", exc)


class CampusMapDialog(QDialog):
    """校园地图态势图对话框。"""

    def __init__(self, cameras: list, tile_by_id: dict,
                 map_bg_path: str = "", layout_path: str = "",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("校园火情态势图")
        self.resize(900, 650)
        self._layout_path = layout_path
        self._map_bg_path = map_bg_path

        layout = QVBoxLayout(self)

        # 顶部控制栏
        top_row = QHBoxLayout()
        btn_load_map = QPushButton("加载地图")
        btn_load_map.clicked.connect(self._load_map_image)
        btn_save = QPushButton("保存布局")
        btn_save.clicked.connect(self._save_layout)
        hint = QLabel("拖拽摄像头图标到对应位置 | 点击图标查看画面")
        hint.setStyleSheet("color: #9ca3af; font-size: 11px;")
        top_row.addWidget(btn_load_map)
        top_row.addWidget(btn_save)
        top_row.addStretch()
        top_row.addWidget(hint)
        layout.addLayout(top_row)

        # 地图组件
        self.map_widget = CampusMapWidget()
        self.map_widget.set_cameras(cameras)
        layout.addWidget(self.map_widget, stretch=1)

        # 加载已有底图和布局
        if map_bg_path and os.path.exists(map_bg_path):
            self.map_widget.load_background(map_bg_path)
        if layout_path:
            self.map_widget.load_layout(layout_path)

    def _load_map_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择校园平面图", "",
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if path:
            if self.map_widget.load_background(path):
                self._map_bg_path = path
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "加载失败", "无法加载该图片文件")

    def _save_layout(self):
        if self._layout_path:
            self.map_widget.save_layout(self._layout_path)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "保存成功", "地图布局已保存")
