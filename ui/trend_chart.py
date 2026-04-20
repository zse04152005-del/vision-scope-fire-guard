"""实时面积趋势折线图组件 — 用 QPainter 绘制火焰面积变化曲线。"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QColor, QFont


# 趋势对应颜色
_TREND_COLORS = {
    "stable": QColor("#22c55e"),    # 绿色
    "growing": QColor("#f59e0b"),   # 橙色
    "spreading": QColor("#ef4444"),  # 红色
}


class TrendChartWidget(QWidget):
    """小型折线图，显示火焰面积随时间变化的趋势。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(70)
        self.setMaximumHeight(100)
        self._data: list = []       # list of (relative_time, area)
        self._trend: str = "stable"
        self._cam_id: str = ""

    def set_data(self, data: list, trend: str = "stable", cam_id: str = ""):
        """更新数据和趋势。data 为 [(时间秒, 面积比例), ...]"""
        self._data = data
        self._trend = trend
        self._cam_id = cam_id
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 8

        # 背景
        painter.fillRect(0, 0, w, h, QColor("#1a1d23"))

        # 边框
        border_color = _TREND_COLORS.get(self._trend, QColor("#3a3f4b"))
        painter.setPen(QPen(border_color, 1))
        painter.drawRect(0, 0, w - 1, h - 1)

        if not self._data or len(self._data) < 2:
            painter.setPen(QColor("#6b7280"))
            painter.setFont(QFont("Sans Serif", 9))
            painter.drawText(margin, h // 2 + 4, "等待数据...")
            painter.end()
            return

        # 绘图区域
        plot_x = margin
        plot_y = margin + 12
        plot_w = w - margin * 2
        plot_h = h - margin * 2 - 16

        # 标题行
        painter.setPen(QColor("#d1d5db"))
        painter.setFont(QFont("Sans Serif", 8))
        trend_label = {"stable": "稳定", "growing": "增长中", "spreading": "蔓延!"}
        label = f"{self._cam_id}  趋势: {trend_label.get(self._trend, self._trend)}"
        painter.drawText(plot_x, margin + 8, label)

        # 数据范围
        areas = [a for _, a in self._data]
        max_area = max(areas) if areas else 1.0
        if max_area <= 0:
            max_area = 1.0
        time_span = self._data[-1][0] - self._data[0][0]
        if time_span <= 0:
            time_span = 1.0

        # 绘制折线
        line_color = _TREND_COLORS.get(self._trend, QColor("#60a5fa"))
        painter.setPen(QPen(line_color, 2))

        points = []
        for t, area in self._data:
            x = plot_x + int((t - self._data[0][0]) / time_span * plot_w)
            y = plot_y + plot_h - int(area / max_area * plot_h)
            points.append((x, y))

        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])

        # 最新值标注
        if points:
            last_x, last_y = points[-1]
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Sans Serif", 8))
            pct = areas[-1] * 100
            painter.drawText(last_x - 30, last_y - 4, f"{pct:.1f}%")

        painter.end()
