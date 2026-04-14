"""右下角 Toast 通知控件。告警等场景下滑入显示，3 秒自动消失。"""
from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, QRect
from PyQt6.QtWidgets import QLabel, QWidget


class Toast(QLabel):
    def __init__(self, parent: QWidget, text: str, level: str = "info", duration_ms: int = 3000):
        super().__init__(parent)
        self.setText(text)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        bg = {
            "info": "#2a2d36",
            "success": "#1a7f37",
            "warning": "#d97706",
            "danger": "#c0392b",
        }.get(level, "#2a2d36")
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                color: #ffffff;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid rgba(255,255,255,0.08);
            }}
            """
        )
        self.setFixedWidth(320)
        self.adjustSize()
        self._duration_ms = duration_ms
        self._anim_in = None
        self._anim_out = None

    def show_at(self, end_rect: QRect) -> None:
        start_rect = QRect(end_rect)
        start_rect.moveLeft(self.parent().width() + 10)
        self.setGeometry(start_rect)
        self.show()
        self.raise_()
        self._anim_in = QPropertyAnimation(self, b"geometry")
        self._anim_in.setDuration(280)
        self._anim_in.setStartValue(start_rect)
        self._anim_in.setEndValue(end_rect)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_in.start()
        QTimer.singleShot(self._duration_ms, self._slide_out)

    def _slide_out(self) -> None:
        if not self.parent():
            self.deleteLater()
            return
        cur = self.geometry()
        end = QRect(cur)
        end.moveLeft(self.parent().width() + 10)
        self._anim_out = QPropertyAnimation(self, b"geometry")
        self._anim_out.setDuration(280)
        self._anim_out.setStartValue(cur)
        self._anim_out.setEndValue(end)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_out.finished.connect(self.deleteLater)
        self._anim_out.start()


class ToastManager:
    """在父窗口右下角堆叠管理多个 Toast。"""

    def __init__(self, parent: QWidget, margin: int = 16, gap: int = 8):
        self.parent = parent
        self.margin = margin
        self.gap = gap
        self._toasts: list[Toast] = []

    def show(self, text: str, level: str = "info", duration_ms: int = 3000) -> None:
        toast = Toast(self.parent, text, level=level, duration_ms=duration_ms)
        toast.destroyed.connect(lambda *_: self._remove(toast))
        self._toasts.append(toast)
        self._relayout()

    def _remove(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        try:
            self._relayout()
        except RuntimeError:
            # 父窗口已销毁
            self._toasts.clear()

    def _relayout(self) -> None:
        try:
            pw = self.parent.width()
            ph = self.parent.height()
        except RuntimeError:
            self._toasts.clear()
            return
        y = ph - self.margin
        for t in reversed(self._toasts):
            h = t.sizeHint().height()
            w = t.width()
            y -= h
            rect = QRect(pw - w - self.margin, y, w, h)
            if t.isVisible():
                t.setGeometry(rect)
            else:
                t.show_at(rect)
            y -= self.gap
