"""UI panel factory functions — extracted from MainWindow.setup_ui to reduce main file size."""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QGroupBox, QLineEdit, QComboBox, QTableWidget,
    QHeaderView, QGridLayout, QSpinBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


def build_status_bar(window, cameras, title: str):
    """Build the top status bar and attach label widgets to *window*."""
    layout = QHBoxLayout()
    title_label = QLabel(title)
    title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
    window.lbl_online = QLabel(f"在线: 0/{len(cameras)}")
    window.lbl_alerts = QLabel("今日告警: 0")
    window.lbl_gpu = QLabel("CPU: - | 内存: - | GPU: -")
    window.lbl_net = QLabel("网络: 正常")
    window.lbl_time = QLabel("时间: --:--")
    layout.addWidget(title_label)
    layout.addStretch()
    layout.addWidget(window.lbl_online)
    layout.addWidget(window.lbl_alerts)
    layout.addWidget(window.lbl_gpu)
    layout.addWidget(window.lbl_net)
    layout.addWidget(window.lbl_time)
    container = QWidget()
    container.setLayout(layout)
    return container


def build_control_tab(window, theme, theme_name: str):
    """Build Tab 1 (控制台) and attach interactive widgets to *window*."""
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(6, 6, 6, 6)
    layout.setSpacing(6)

    gb_source = QGroupBox("视频源控制")
    layout_source = QGridLayout()
    window.btn_open_cam = QPushButton("▶  启动全部")
    window.btn_stop = QPushButton("■  停止全部")
    window.btn_open_cam.clicked.connect(window.start_all)
    window.btn_stop.clicked.connect(window.stop_all)
    layout_source.addWidget(window.btn_open_cam, 0, 0)
    layout_source.addWidget(window.btn_stop, 0, 1)
    window.btn_video = QPushButton("▤  导入视频")
    window.btn_img = QPushButton("▦  导入图片")
    window.btn_video.clicked.connect(window.select_video)
    window.btn_img.clicked.connect(window.select_image)
    layout_source.addWidget(window.btn_video, 1, 0)
    layout_source.addWidget(window.btn_img, 1, 1)
    window.btn_pause = QPushButton("‖  暂停全部")
    window.btn_pause.clicked.connect(window.toggle_pause)
    layout_source.addWidget(window.btn_pause, 2, 0, 1, 2)
    window.btn_manage = QPushButton("⚙  摄像头管理")
    window.btn_manage.clicked.connect(window.open_camera_manager)
    layout_source.addWidget(window.btn_manage, 3, 0, 1, 2)
    window.btn_mute = QPushButton("✕  消音 (ESC)")
    window.btn_mute.clicked.connect(window.dismiss_alert)
    layout_source.addWidget(window.btn_mute, 4, 0, 1, 2)
    gb_source.setLayout(layout_source)
    layout.addWidget(gb_source)

    gb_param = QGroupBox("参数调节")
    layout_param = QVBoxLayout()
    row_conf = QHBoxLayout()
    row_conf.addWidget(QLabel("置信度:"))
    window.conf_spin = QSpinBox()
    window.conf_spin.setRange(0, 100)
    window.conf_spin.setValue(50)
    row_conf.addWidget(window.conf_spin)
    layout_param.addLayout(row_conf)
    window.conf_slider = QSlider(Qt.Orientation.Horizontal)
    window.conf_slider.setRange(0, 100)
    window.conf_slider.setValue(50)
    window.conf_slider.valueChanged.connect(window.update_conf)
    layout_param.addWidget(window.conf_slider)
    window.btn_advisor = QPushButton("智能阈值顾问")
    window.btn_advisor.clicked.connect(window.open_threshold_advisor)
    layout_param.addWidget(window.btn_advisor)
    gb_param.setLayout(layout_param)
    layout.addWidget(gb_param)

    row_misc = QHBoxLayout()
    btn_snap = QPushButton("◉  保存截图")
    btn_snap.setStyleSheet(
        f"background-color: {theme.danger}; color: #ffffff; font-weight: bold; border: none;"
    )
    btn_snap.clicked.connect(window.save_screenshot)
    btn_snap.setFixedHeight(42)
    row_misc.addWidget(btn_snap)
    window.btn_theme = QPushButton("切换浅色" if theme_name == "dark" else "切换深色")
    window.btn_theme.clicked.connect(window.toggle_theme)
    window.btn_theme.setFixedHeight(42)
    row_misc.addWidget(window.btn_theme)
    layout.addLayout(row_misc)

    window.btn_heatmap = QPushButton("开启热力图")
    window.btn_heatmap.clicked.connect(window.toggle_heatmap)
    layout.addWidget(window.btn_heatmap)

    layout.addStretch()
    return tab


def build_alarm_tab(window):
    """Build Tab 2 (告警中心) and attach table/filter widgets to *window*."""
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(6, 6, 6, 6)
    layout.setSpacing(6)

    filter_row = QHBoxLayout()
    window.alarm_search = QLineEdit()
    window.alarm_search.setPlaceholderText("搜索摄像头/时间")
    window.alarm_level = QComboBox()
    window.alarm_level.addItems(["all", "confirm", "warn"])
    window.alarm_search.textChanged.connect(window.refresh_alarm_table)
    window.alarm_level.currentTextChanged.connect(window.refresh_alarm_table)
    window.btn_export = QPushButton("导出")
    window.btn_export.clicked.connect(window.export_alarms)
    filter_row.addWidget(window.alarm_search)
    filter_row.addWidget(window.alarm_level)
    filter_row.addWidget(window.btn_export)
    layout.addLayout(filter_row)

    # 历史时间轴
    from ui.timeline_widget import TimelineWidget
    window.timeline = TimelineWidget()
    window.timeline.alarm_clicked.connect(window.on_timeline_click)
    layout.addWidget(window.timeline)

    window.alarm_table = QTableWidget()
    window.alarm_table.setColumnCount(4)
    window.alarm_table.setHorizontalHeaderLabels(["时间", "摄像头", "等级", "状态"])
    window.alarm_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    window.alarm_table.cellDoubleClicked.connect(window.open_alarm_detail)
    layout.addWidget(window.alarm_table, stretch=1)

    gb_stats = QGroupBox("告警统计")
    stats_layout = QVBoxLayout()
    window.lbl_alarm_total = QLabel("今日总计: 0")
    window.lbl_alarm_top_cam = QLabel("最频繁: -")
    window.lbl_alarm_avg_conf = QLabel("平均置信度: -")
    stats_layout.addWidget(window.lbl_alarm_total)
    stats_layout.addWidget(window.lbl_alarm_top_cam)
    stats_layout.addWidget(window.lbl_alarm_avg_conf)
    gb_stats.setLayout(stats_layout)
    layout.addWidget(gb_stats)

    return tab


def build_status_tab(window, theme):
    """Build Tab 3 (系统状态) and attach info/detail widgets to *window*."""
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(6, 6, 6, 6)
    layout.setSpacing(6)

    gb_info = QGroupBox("实时信息")
    layout_info = QVBoxLayout()
    window.lbl_status = QLabel("状态: 待机")
    window.lbl_fps = QLabel("用时: 0.00s")
    window.lbl_count = QLabel("目标数: 0")
    window.lbl_conf_large = QLabel("0.00%")
    window.lbl_conf_large.setStyleSheet(
        f"font-size: 24px; color: {theme.primary}; font-weight: bold;"
    )
    window.lbl_conf_large.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout_info.addWidget(window.lbl_status)
    layout_info.addWidget(window.lbl_fps)
    layout_info.addWidget(window.lbl_count)
    layout_info.addWidget(QLabel("最高置信度:"))
    layout_info.addWidget(window.lbl_conf_large)
    gb_info.setLayout(layout_info)
    layout.addWidget(gb_info)

    gb_detail = QGroupBox("检测详情")
    detail_layout = QVBoxLayout()
    window.result_table = QTableWidget()
    window.result_table.setColumnCount(4)
    window.result_table.setHorizontalHeaderLabels(["序号", "类别", "置信度", "坐标"])
    window.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    detail_layout.addWidget(window.result_table)
    gb_detail.setLayout(detail_layout)
    layout.addWidget(gb_detail, stretch=1)

    # 火焰蔓延趋势图
    from ui.trend_chart import TrendChartWidget
    gb_trend = QGroupBox("火焰蔓延趋势")
    trend_layout = QVBoxLayout()
    window.trend_chart = TrendChartWidget()
    trend_layout.addWidget(window.trend_chart)
    gb_trend.setLayout(trend_layout)
    layout.addWidget(gb_trend)

    return tab
