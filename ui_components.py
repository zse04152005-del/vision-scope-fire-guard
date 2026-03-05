from typing import List, Tuple

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QWidget, QSizePolicy, QScrollArea
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QImage, QPixmap, QDrag
from PyQt6.QtCore import QMimeData


def build_grid_positions(count: int, cols: int) -> List[Tuple[int, int]]:
    return [(i // cols, i % cols) for i in range(count)]


CAM_TILE_MIN_W = 240
CAM_TILE_MIN_H = 180


def compute_grid_cols(available_width: int, tile_w: int, spacing: int, max_cols: int) -> int:
    if max_cols <= 1:
        return 1
    for cols in range(max_cols, 0, -1):
        width = cols * tile_w + spacing * (cols - 1)
        if width <= available_width:
            return cols
    return 1


def resolve_grid_cols(
    config_cols: int | None,
    available_width: int,
    tile_w: int,
    spacing: int,
    max_cols: int,
) -> int:
    if config_cols is not None and config_cols > 0:
        return min(config_cols, max_cols)
    return compute_grid_cols(available_width, tile_w, spacing, max_cols)


def compute_available_grid_width(window_width: int, right_width: int, padding: int) -> int:
    return max(0, window_width - right_width - padding)


def compute_grid_min_size(tile_w: int, tile_h: int, rows: int, cols: int, spacing: int) -> QSize:
    width = cols * tile_w + spacing * (cols - 1)
    height = rows * tile_h + spacing * (rows - 1)
    return QSize(width, height)


def build_scroll_area(widget: QWidget, always_show_vertical: bool = False) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(widget)
    scroll.setVerticalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOn if always_show_vertical else Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return scroll


class CameraTile(QWidget):
    swapRequested = pyqtSignal(str, str)
    zoomRequested = pyqtSignal(str)

    def __init__(self, name: str):
        super().__init__()
        self.cam_id = name
        self.setMinimumSize(CAM_TILE_MIN_W, CAM_TILE_MIN_H)
        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.name_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))

        self.status_label = QLabel("OFFLINE")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_label.setStyleSheet("color: #999;")

        header = QHBoxLayout()
        header.addWidget(self.name_label)
        header.addWidget(self.status_label)

        self.video_label = QLabel("等待视频输入...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #222; border: 1px solid #444;")
        self.video_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.video_label.setScaledContents(True)

        self.meta_label = QLabel("FPS: 0  |  目标: 0")
        self.meta_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.meta_label.setStyleSheet("color: #666;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        layout.addLayout(header)
        layout.addWidget(self.video_label, stretch=1)
        layout.addWidget(self.meta_label)

        self.setAcceptDrops(True)
        self._drag_start = QPoint()

    def set_frame(self, img: QImage) -> None:
        self.video_label.setPixmap(QPixmap.fromImage(img))

    def set_status(self, text: str, color: str = "#999") -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < 8:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.cam_id)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        source_id = event.mimeData().text()
        if source_id and source_id != self.cam_id:
            self.swapRequested.emit(source_id, self.cam_id)
        event.acceptProposedAction()

    def mouseDoubleClickEvent(self, event):
        self.zoomRequested.emit(self.cam_id)
        super().mouseDoubleClickEvent(event)
