"""UI 主题定义（深色/浅色）。集中管理颜色、字体、QSS，便于一键切换。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    bg_alt: str
    panel: str
    border: str
    text: str
    text_muted: str
    primary: str
    primary_hover: str
    success: str
    warning: str
    danger: str
    video_bg: str
    tile_border: str


DARK = Theme(
    name="dark",
    bg="#1b1d23",
    bg_alt="#23262e",
    panel="#2a2d36",
    border="#3a3f4b",
    text="#e6e8ef",
    text_muted="#9aa0ac",
    primary="#4ea3ff",
    primary_hover="#1890ff",
    success="#2ecc71",
    warning="#f0a000",
    danger="#ff3b30",
    video_bg="#0e1014",
    tile_border="#3a3f4b",
)

LIGHT = Theme(
    name="light",
    bg="#f3f5f9",
    bg_alt="#ffffff",
    panel="#ffffff",
    border="#d9dde5",
    text="#1f2430",
    text_muted="#6b7280",
    primary="#1890ff",
    primary_hover="#0a6ac2",
    success="#1a7f37",
    warning="#d97706",
    danger="#d4380d",
    video_bg="#222222",
    tile_border="#d9dde5",
)

THEMES = {"dark": DARK, "light": LIGHT}


def get_theme(name: str | None) -> Theme:
    return THEMES.get((name or "dark").lower(), DARK)


def build_qss(t: Theme) -> str:
    return f"""
        QMainWindow, QDialog {{ background-color: {t.bg}; }}
        QWidget {{ color: {t.text}; font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; font-size: 13px; }}
        QLabel {{ color: {t.text}; background: transparent; }}
        QGroupBox {{
            background-color: {t.panel};
            border: 1px solid {t.border};
            border-radius: 8px;
            margin-top: 14px;
            padding: 10px 8px 8px 8px;
            font-weight: bold;
            color: {t.text};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {t.primary};
        }}
        QPushButton {{
            background-color: {t.bg_alt};
            color: {t.text};
            border: 1px solid {t.border};
            border-radius: 6px;
            padding: 7px 10px;
        }}
        QPushButton:hover {{
            background-color: {t.panel};
            border-color: {t.primary};
            color: {t.primary};
        }}
        QPushButton:pressed {{ background-color: {t.border}; }}
        QLineEdit, QComboBox, QSpinBox {{
            background-color: {t.bg_alt};
            color: {t.text};
            border: 1px solid {t.border};
            border-radius: 5px;
            padding: 4px 6px;
            selection-background-color: {t.primary};
        }}
        QComboBox QAbstractItemView {{
            background-color: {t.bg_alt};
            color: {t.text};
            selection-background-color: {t.primary};
        }}
        QSlider::groove:horizontal {{
            height: 6px; background: {t.border}; border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {t.primary};
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
        QTableWidget {{
            background-color: {t.bg_alt};
            color: {t.text};
            gridline-color: {t.border};
            border: 1px solid {t.border};
            selection-background-color: {t.primary};
            selection-color: #ffffff;
        }}
        QHeaderView::section {{
            background-color: {t.panel};
            color: {t.text_muted};
            border: none;
            padding: 6px;
            border-bottom: 1px solid {t.border};
        }}
        QScrollArea {{ background: transparent; border: none; }}
        QScrollBar:vertical {{
            background: {t.bg}; width: 10px; margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {t.border}; border-radius: 5px; min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {t.primary}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QToolTip {{
            background-color: {t.panel};
            color: {t.text};
            border: 1px solid {t.border};
            padding: 4px;
        }}
    """
