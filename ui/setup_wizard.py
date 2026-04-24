"""首次使用设置向导 — 引导新用户添加摄像头并完成基本配置。"""

import cv2
from threading import Thread

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QWidget, QLineEdit, QComboBox,
    QGridLayout, QMessageBox, QGroupBox, QRadioButton,
    QButtonGroup, QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap

from ui.camera_manager import detect_local_cameras, PreviewWidget
from utils.camera_config import normalize_source, save_cameras


class SetupWizard(QDialog):
    """首次运行设置向导。

    三步引导：
    1. 欢迎页 — 介绍系统
    2. 添加摄像头 — 自动检测 + 手动输入
    3. 完成页 — 确认并启动
    """

    def __init__(self, config_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("VisionScope 设置向导")
        self.resize(640, 480)
        self.setModal(True)
        self.config_path = config_path
        self._cameras: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # 页面容器
        self.pages = QStackedWidget()
        layout.addWidget(self.pages, stretch=1)

        # 底部导航
        nav = QHBoxLayout()
        self.btn_back = QPushButton("上一步")
        self.btn_back.clicked.connect(self._prev_page)
        self.btn_next = QPushButton("下一步")
        self.btn_next.clicked.connect(self._next_page)
        self.btn_next.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold;")
        self.btn_next.setFixedHeight(38)
        self.btn_back.setFixedHeight(38)
        self.lbl_step = QLabel("1 / 3")
        self.lbl_step.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_step.setStyleSheet("color: #9ca3af;")
        nav.addWidget(self.btn_back)
        nav.addWidget(self.lbl_step, stretch=1)
        nav.addWidget(self.btn_next)
        layout.addLayout(nav)

        # 构建三个页面
        self.pages.addWidget(self._build_welcome_page())
        self.pages.addWidget(self._build_camera_page())
        self.pages.addWidget(self._build_finish_page())

        self._update_nav()

    # --------- 页面构建 ---------

    def _build_welcome_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("欢迎使用 VisionScope")
        title.setFont(QFont("Sans Serif", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("校园多路火警监控系统")
        subtitle.setFont(QFont("Sans Serif", 12))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #9ca3af;")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        features = QLabel(
            "本向导将帮助您完成初始设置：\n\n"
            "  1. 添加摄像头（USB / 网络 / 视频文件）\n"
            "  2. 验证摄像头连接\n"
            "  3. 开始实时监控\n\n"
            "您也可以稍后在「摄像头管理」中修改配置。"
        )
        features.setFont(QFont("Sans Serif", 11))
        features.setStyleSheet("color: #d1d5db; line-height: 1.6;")
        layout.addWidget(features)

        layout.addStretch()
        return page

    def _build_camera_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        title = QLabel("添加摄像头")
        title.setFont(QFont("Sans Serif", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # 方式选择
        type_group = QGroupBox("选择添加方式")
        type_layout = QVBoxLayout()
        self._radio_local = QRadioButton("本地 USB 摄像头（自动检测）")
        self._radio_rtsp = QRadioButton("网络摄像头（RTSP / HTTP）")
        self._radio_file = QRadioButton("视频文件")
        self._radio_local.setChecked(True)
        self._btn_group = QButtonGroup()
        self._btn_group.addButton(self._radio_local, 0)
        self._btn_group.addButton(self._radio_rtsp, 1)
        self._btn_group.addButton(self._radio_file, 2)
        self._btn_group.idToggled.connect(self._on_type_changed)
        type_layout.addWidget(self._radio_local)
        type_layout.addWidget(self._radio_rtsp)
        type_layout.addWidget(self._radio_file)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # 输入区（堆叠）
        self._input_stack = QStackedWidget()

        # 本地：自动检测按钮
        local_widget = QWidget()
        local_lay = QVBoxLayout(local_widget)
        self._btn_scan = QPushButton("扫描本地摄像头")
        self._btn_scan.clicked.connect(self._scan_local)
        self._lbl_scan_result = QLabel("点击扫描按钮检测可用摄像头")
        self._lbl_scan_result.setStyleSheet("color: #9ca3af;")
        local_lay.addWidget(self._btn_scan)
        local_lay.addWidget(self._lbl_scan_result)
        self._local_btn_layout = QHBoxLayout()
        local_lay.addLayout(self._local_btn_layout)
        self._scan_buttons: list[QPushButton] = []
        self._input_stack.addWidget(local_widget)

        # RTSP 输入
        rtsp_widget = QWidget()
        rtsp_lay = QGridLayout(rtsp_widget)
        rtsp_lay.addWidget(QLabel("名称:"), 0, 0)
        self._wiz_name = QLineEdit()
        self._wiz_name.setPlaceholderText("如: A楼走廊")
        rtsp_lay.addWidget(self._wiz_name, 0, 1, 1, 2)
        rtsp_lay.addWidget(QLabel("地址:"), 1, 0)
        self._wiz_url = QLineEdit()
        self._wiz_url.setPlaceholderText("rtsp://admin:password@192.168.1.100:554/stream1")
        rtsp_lay.addWidget(self._wiz_url, 1, 1, 1, 2)
        btn_add_rtsp = QPushButton("添加")
        btn_add_rtsp.clicked.connect(self._add_rtsp)
        rtsp_lay.addWidget(btn_add_rtsp, 2, 2)
        self._input_stack.addWidget(rtsp_widget)

        # 文件选择
        file_widget = QWidget()
        file_lay = QHBoxLayout(file_widget)
        btn_browse = QPushButton("浏览文件...")
        btn_browse.clicked.connect(self._browse_file)
        self._lbl_file = QLabel("")
        self._lbl_file.setStyleSheet("color: #9ca3af;")
        file_lay.addWidget(btn_browse)
        file_lay.addWidget(self._lbl_file, stretch=1)
        self._input_stack.addWidget(file_widget)

        layout.addWidget(self._input_stack)

        # 已添加列表
        self._lbl_added = QLabel("已添加: 0 个摄像头")
        self._lbl_added.setStyleSheet("color: #22c55e; font-weight: bold;")
        layout.addWidget(self._lbl_added)

        layout.addStretch()
        return page

    def _build_finish_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("设置完成!")
        title.setFont(QFont("Sans Serif", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(20)

        self._lbl_summary = QLabel("")
        self._lbl_summary.setFont(QFont("Sans Serif", 11))
        self._lbl_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_summary.setStyleSheet("color: #d1d5db;")
        layout.addWidget(self._lbl_summary)

        layout.addSpacing(20)

        hint = QLabel(
            "点击「完成」保存配置并启动系统。\n\n"
            "之后您可以随时通过「摄像头管理」修改配置。"
        )
        hint.setFont(QFont("Sans Serif", 10))
        hint.setStyleSheet("color: #9ca3af;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch()
        return page

    # --------- 导航 ---------

    def _update_nav(self):
        idx = self.pages.currentIndex()
        total = self.pages.count()
        self.lbl_step.setText(f"{idx + 1} / {total}")
        self.btn_back.setVisible(idx > 0)
        if idx == total - 1:
            self.btn_next.setText("完成")
        else:
            self.btn_next.setText("下一步")

    def _prev_page(self):
        idx = self.pages.currentIndex()
        if idx > 0:
            self.pages.setCurrentIndex(idx - 1)
            self._update_nav()

    def _next_page(self):
        idx = self.pages.currentIndex()
        total = self.pages.count()

        if idx == 1:
            # 验证至少添加了一个摄像头
            if not self._cameras:
                QMessageBox.warning(self, "提示", "请至少添加一个摄像头")
                return
            # 更新完成页摘要
            names = [c.get("name", c["id"]) for c in self._cameras]
            self._lbl_summary.setText(
                f"已配置 {len(self._cameras)} 个摄像头:\n\n" +
                "\n".join(f"  - {n}" for n in names)
            )

        if idx < total - 1:
            self.pages.setCurrentIndex(idx + 1)
            self._update_nav()
        else:
            # 完成 → 保存并关闭
            self._finish()

    def _finish(self):
        save_cameras(self.config_path, self._cameras)
        self.accept()

    # --------- 交互逻辑 ---------

    def _on_type_changed(self, btn_id: int, checked: bool):
        if checked:
            self._input_stack.setCurrentIndex(btn_id)

    def _scan_local(self):
        self._btn_scan.setEnabled(False)
        self._lbl_scan_result.setText("正在扫描...")
        for btn in self._scan_buttons:
            btn.deleteLater()
        self._scan_buttons.clear()

        def _run():
            found = detect_local_cameras()
            QTimer.singleShot(0, lambda: self._on_scan_done(found))

        Thread(target=_run, daemon=True).start()

    def _on_scan_done(self, found: list[dict]):
        self._btn_scan.setEnabled(True)
        if not found:
            self._lbl_scan_result.setText("未检测到摄像头，请确认设备已连接")
            return
        self._lbl_scan_result.setText(f"检测到 {len(found)} 个摄像头，点击添加:")
        for cam in found:
            idx = cam["index"]
            res = cam["resolution"]
            btn = QPushButton(f"摄像头 {idx} ({res})")
            btn.clicked.connect(
                lambda checked, i=idx, r=res: self._add_camera(f"本地摄像头-{i}", i)
            )
            self._local_btn_layout.addWidget(btn)
            self._scan_buttons.append(btn)

    def _add_rtsp(self):
        url = self._wiz_url.text().strip()
        if not url:
            QMessageBox.warning(self, "提示", "请输入摄像头地址")
            return
        name = self._wiz_name.text().strip() or url.split("@")[-1].split("/")[0]
        self._add_camera(name, url)
        self._wiz_name.clear()
        self._wiz_url.clear()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "Videos (*.mp4 *.avi *.mkv *.mov)"
        )
        if path:
            import os
            name = os.path.splitext(os.path.basename(path))[0]
            self._add_camera(name, path)
            self._lbl_file.setText(f"已添加: {os.path.basename(path)}")

    def _add_camera(self, name: str, source) -> None:
        cam_id = f"cam{len(self._cameras) + 1:02d}"
        self._cameras.append({"id": cam_id, "name": name, "source": source})
        self._lbl_added.setText(f"已添加: {len(self._cameras)} 个摄像头")

    def get_cameras(self) -> list[dict]:
        return list(self._cameras)
