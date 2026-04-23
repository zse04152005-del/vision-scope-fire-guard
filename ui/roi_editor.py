"""ROI 编辑器 — 在摄像头画面上鼠标绘制多边形关注区域。"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox,
    QMessageBox, QWidget,
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPixmap, QImage, QMouseEvent, QPolygonF


class ROICanvas(QWidget):
    """可交互画布：在摄像头截图上绘制多边形 ROI。"""

    def __init__(self, pixmap: QPixmap, existing_polygons: list = None, parent=None):
        super().__init__(parent)
        self._base_pixmap = pixmap
        self._polygons: list[list[tuple[float, float]]] = list(existing_polygons or [])
        self._current_points: list[QPointF] = []
        self._hover_pos: QPointF | None = None
        self.setMinimumSize(640, 480)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    @property
    def polygons(self) -> list[list[tuple[float, float]]]:
        return list(self._polygons)

    def _to_normalized(self, pos: QPointF) -> tuple[float, float]:
        """将画布坐标转为归一化坐标 (0~1)。"""
        w, h = self.width(), self.height()
        return (max(0.0, min(1.0, pos.x() / w)),
                max(0.0, min(1.0, pos.y() / h)))

    def _from_normalized(self, nx: float, ny: float) -> QPointF:
        """将归一化坐标转为画布坐标。"""
        return QPointF(nx * self.width(), ny * self.height())

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._current_points.append(event.position())
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键完成当前多边形
            if len(self._current_points) >= 3:
                poly = [self._to_normalized(p) for p in self._current_points]
                self._polygons.append(poly)
                self._current_points = []
                self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        self._hover_pos = event.position()
        self.update()

    def undo_last_point(self):
        if self._current_points:
            self._current_points.pop()
        elif self._polygons:
            self._polygons.pop()
        self.update()

    def clear_all(self):
        self._polygons.clear()
        self._current_points.clear()
        self.update()

    def finish_current(self):
        if len(self._current_points) >= 3:
            poly = [self._to_normalized(p) for p in self._current_points]
            self._polygons.append(poly)
            self._current_points = []
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制底图
        if self._base_pixmap and not self._base_pixmap.isNull():
            scaled = self._base_pixmap.scaled(
                self.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(0, 0, scaled)
        else:
            painter.fillRect(self.rect(), QColor("#1a1d23"))
            painter.setPen(QColor("#6b7280"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "无画面，请先启动摄像头")

        # 绘制已完成的多边形
        for poly_norm in self._polygons:
            self._draw_polygon(painter, poly_norm, completed=True)

        # 绘制正在画的多边形
        if self._current_points:
            pen = QPen(QColor("#22c55e"), 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            for i in range(len(self._current_points) - 1):
                painter.drawLine(self._current_points[i], self._current_points[i + 1])

            # 连接到鼠标位置的虚线
            if self._hover_pos:
                painter.setPen(QPen(QColor("#86efac"), 1, Qt.PenStyle.DotLine))
                painter.drawLine(self._current_points[-1], self._hover_pos)
                # 闭合预览线
                if len(self._current_points) >= 2:
                    painter.drawLine(self._current_points[0], self._hover_pos)

            # 绘制顶点
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#22c55e")))
            for pt in self._current_points:
                painter.drawEllipse(pt, 4, 4)

        painter.end()

    def _draw_polygon(self, painter: QPainter, poly_norm: list, completed: bool = True):
        points = [self._from_normalized(x, y) for x, y in poly_norm]
        qpoly = QPolygonF(points)

        # 半透明填充
        fill_color = QColor("#22c55e") if completed else QColor("#60a5fa")
        fill_color.setAlpha(40)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(fill_color))
        painter.drawPolygon(qpoly)

        # 边框
        border_color = QColor("#22c55e") if completed else QColor("#60a5fa")
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(qpoly)

        # 顶点
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(border_color))
        for pt in points:
            painter.drawEllipse(pt, 3, 3)


class ROIEditorDialog(QDialog):
    """ROI 编辑对话框 — 选择摄像头，在画面上绘制多边形区域。"""

    def __init__(self, roi_manager, cameras: list, tile_by_id: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ROI 关注区域编辑")
        self.resize(800, 620)
        self._roi_manager = roi_manager
        self._cameras = cameras
        self._tile_by_id = tile_by_id

        layout = QVBoxLayout(self)

        # 顶部：选择摄像头
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("摄像头:"))
        self._cam_combo = QComboBox()
        for cam in cameras:
            cam_id = cam.get("id", "")
            name = cam.get("name", cam_id)
            self._cam_combo.addItem(f"{name} ({cam_id})", cam_id)
        self._cam_combo.currentIndexChanged.connect(self._on_cam_changed)
        top_row.addWidget(self._cam_combo, stretch=1)
        layout.addLayout(top_row)

        # 提示
        hint = QLabel("左键点击添加顶点 | 右键完成当前多边形 | 可绘制多个区域")
        hint.setStyleSheet("color: #9ca3af; font-size: 11px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        # 画布
        self._canvas = ROICanvas(QPixmap(), parent=self)
        layout.addWidget(self._canvas, stretch=1)

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_undo = QPushButton("撤销 (Ctrl+Z)")
        btn_undo.clicked.connect(self._canvas.undo_last_point)
        btn_finish = QPushButton("完成当前区域")
        btn_finish.clicked.connect(self._canvas.finish_current)
        btn_clear = QPushButton("清除全部")
        btn_clear.clicked.connect(self._canvas.clear_all)
        btn_save = QPushButton("保存")
        btn_save.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold;")
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_undo)
        btn_row.addWidget(btn_finish)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        # 加载第一个摄像头
        if cameras:
            self._on_cam_changed(0)

    def _current_cam_id(self) -> str:
        return self._cam_combo.currentData() or ""

    def _on_cam_changed(self, _index: int):
        cam_id = self._current_cam_id()
        # 获取当前帧截图
        pixmap = QPixmap()
        tile = self._tile_by_id.get(cam_id)
        if tile and tile.video_label.pixmap() and not tile.video_label.pixmap().isNull():
            pixmap = tile.video_label.pixmap()

        existing = self._roi_manager.get_roi(cam_id)
        self._canvas._base_pixmap = pixmap
        self._canvas._polygons = list(existing)
        self._canvas._current_points = []
        self._canvas.update()

    def _on_save(self):
        cam_id = self._current_cam_id()
        if not cam_id:
            return

        # 先把正在画的也完成
        self._canvas.finish_current()

        polygons = self._canvas.polygons
        if polygons:
            self._roi_manager.set_roi(cam_id, polygons)
        else:
            self._roi_manager.clear_roi(cam_id)

        self._roi_manager.save()
        QMessageBox.information(self, "保存成功",
                                f"摄像头 {cam_id} 的 ROI 已保存（{len(polygons)} 个区域）")
