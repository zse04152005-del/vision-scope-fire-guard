"""告警时间轴组件 — 24h 可视化时间条，显示告警分布并支持点击跳转。"""

import time
from typing import List, Optional, Callable

from PyQt6.QtWidgets import QWidget, QToolTip
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QMouseEvent


class TimelineWidget(QWidget):
    """水平时间轴，显示一天内告警事件的时间分布。

    点击告警标记会 emit alarm_clicked(event_index)。
    """

    alarm_clicked = pyqtSignal(int)  # index into alarm_events list

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(60)
        self.setMaximumHeight(80)
        self.setMouseTracking(True)
        self._events: List[dict] = []
        self._day_start: float = 0.0  # 当天 00:00 的 timestamp
        self._update_day_start()

    def set_events(self, events: List[dict]):
        """设置告警事件列表（需包含 'ts' 字段）。"""
        self._events = events
        self._update_day_start()
        self.update()

    def _update_day_start(self):
        """计算今天 00:00:00 的 timestamp。"""
        t = time.localtime()
        self._day_start = time.mktime(time.struct_time((
            t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1
        )))

    def _ts_to_x(self, ts: float) -> int:
        """将时间戳转为画布 x 坐标。"""
        margin = 30
        w = self.width() - margin * 2
        seconds_in_day = 86400.0
        offset = max(0.0, min(seconds_in_day, ts - self._day_start))
        return margin + int(offset / seconds_in_day * w)

    def _x_to_ts(self, x: int) -> float:
        """将 x 坐标转回时间戳。"""
        margin = 30
        w = self.width() - margin * 2
        ratio = max(0.0, min(1.0, (x - margin) / max(1, w)))
        return self._day_start + ratio * 86400

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 30
        bar_y = h // 2
        bar_h = 8

        # 背景
        painter.fillRect(0, 0, w, h, QColor("#1a1d23"))

        # 时间轴底条
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2a2f3a"))
        painter.drawRoundedRect(margin, bar_y - bar_h // 2, w - margin * 2, bar_h, 4, 4)

        # 小时刻度
        painter.setPen(QPen(QColor("#4b5563"), 1))
        painter.setFont(QFont("Sans Serif", 7))
        for hour in range(0, 25, 3):
            ts = self._day_start + hour * 3600
            x = self._ts_to_x(ts)
            painter.drawLine(x, bar_y - 12, x, bar_y + 12)
            painter.drawText(x - 8, h - 4, f"{hour:02d}:00")

        # 当前时间指示器
        now_x = self._ts_to_x(time.time())
        painter.setPen(QPen(QColor("#60a5fa"), 2))
        painter.drawLine(now_x, bar_y - 16, now_x, bar_y + 16)

        # 告警标记
        for i, ev in enumerate(self._events):
            ts = ev.get("ts", 0)
            if ts < self._day_start or ts > self._day_start + 86400:
                continue
            x = self._ts_to_x(ts)
            level = ev.get("level", "confirm")
            if level == "spreading":
                color = QColor("#dc2626")
                radius = 5
            elif level == "confirm":
                color = QColor("#f59e0b")
                radius = 4
            else:
                color = QColor("#6b7280")
                radius = 3
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(x - radius, bar_y - radius, radius * 2, radius * 2)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        x = int(event.position().x())
        # 查找最近的告警标记（10px 容差）
        best_idx = -1
        best_dist = 999
        for i, ev in enumerate(self._events):
            ts = ev.get("ts", 0)
            mark_x = self._ts_to_x(ts)
            dist = abs(x - mark_x)
            if dist < 10 and dist < best_dist:
                best_dist = dist
                best_idx = i
        if best_idx >= 0:
            self.alarm_clicked.emit(best_idx)

    def mouseMoveEvent(self, event: QMouseEvent):
        x = int(event.position().x())
        # 显示悬停的时间
        ts = self._x_to_ts(x)
        time_str = time.strftime("%H:%M:%S", time.localtime(ts))
        # 查找最近事件
        for ev in self._events:
            mark_x = self._ts_to_x(ev.get("ts", 0))
            if abs(x - mark_x) < 8:
                cam = ev.get("camera", "")
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    f"{ev.get('time', time_str)} | {cam} | {ev.get('level', '')}"
                )
                return
        QToolTip.showText(event.globalPosition().toPoint(), time_str)
