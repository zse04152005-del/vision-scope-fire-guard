"""摄像头管理 — 自动检测本地摄像头、实时预览、RTSP 地址辅助、一键添加。"""

import cv2
import logging
import time
from threading import Thread

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QLabel, QLineEdit,
    QGroupBox, QGridLayout, QComboBox, QWidget, QSizePolicy, QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QFont

from utils.camera_config import normalize_source, save_cameras

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 自动检测本地摄像头
# ------------------------------------------------------------------

def detect_local_cameras(max_index: int = 8) -> list[dict]:
    """探测可用的本地摄像头索引（0~max_index）。"""
    found = []
    for idx in range(max_index):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            ret, frame = cap.read()
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            found.append({
                "index": idx,
                "resolution": f"{w}x{h}",
                "readable": ret and frame is not None,
            })
        else:
            cap.release()
    return found


# ------------------------------------------------------------------
# 预览组件
# ------------------------------------------------------------------

class PreviewWidget(QLabel):
    """摄像头实时预览，内部用后台线程采集帧。"""

    frame_ready = pyqtSignal(QImage)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setStyleSheet(
            "background-color: #0e1014; border: 1px solid #3a3f4b; "
            "border-radius: 6px; color: #6b7280;"
        )
        self.setText("点击「预览」查看画面")
        self._thread = None
        self._running = False
        self.frame_ready.connect(self._on_frame)

    def start(self, source) -> None:
        self.stop()
        self._running = True
        self._thread = Thread(target=self._capture_loop, args=(source,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def _capture_loop(self, source):
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            self._running = False
            return
        while self._running:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
            self.frame_ready.emit(img.copy())
            time.sleep(0.05)  # ~20fps
        cap.release()

    def _on_frame(self, img: QImage):
        pm = QPixmap.fromImage(img).scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(pm)

    def clear_preview(self):
        self.stop()
        self.clear()
        self.setText("点击「预览」查看画面")


class CameraManager(QDialog):
    """增强版摄像头管理对话框。

    功能：
    - 自动检测本地 USB 摄像头
    - RTSP 地址辅助填写
    - 实时画面预览
    - 一键添加 / 删除 / 测试
    """

    def __init__(self, parent, config_path: str, cameras: list[dict]):
        super().__init__(parent)
        self.setWindowTitle("摄像头管理")
        self.resize(860, 580)
        self.config_path = config_path

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ============ 顶部：快速添加区 ============
        add_tabs = QTabWidget()
        add_tabs.setMaximumHeight(200)

        # Tab 1: 本地摄像头
        tab_local = QWidget()
        local_layout = QVBoxLayout(tab_local)
        local_layout.setContentsMargins(8, 8, 8, 8)

        detect_row = QHBoxLayout()
        self.btn_detect = QPushButton("扫描本地摄像头")
        self.btn_detect.clicked.connect(self._detect_cameras)
        self.lbl_detect_status = QLabel("点击扫描检测可用摄像头")
        self.lbl_detect_status.setStyleSheet("color: #9ca3af;")
        detect_row.addWidget(self.btn_detect)
        detect_row.addWidget(self.lbl_detect_status, stretch=1)
        local_layout.addLayout(detect_row)

        self.local_cam_list = QHBoxLayout()
        self._local_buttons: list[QPushButton] = []
        local_layout.addLayout(self.local_cam_list)
        local_layout.addStretch()
        add_tabs.addTab(tab_local, "本地摄像头")

        # Tab 2: RTSP / 网络摄像头
        tab_rtsp = QWidget()
        rtsp_layout = QGridLayout(tab_rtsp)
        rtsp_layout.setContentsMargins(8, 8, 8, 8)

        rtsp_layout.addWidget(QLabel("名称:"), 0, 0)
        self.rtsp_name = QLineEdit()
        self.rtsp_name.setPlaceholderText("例如: 教学楼走廊")
        rtsp_layout.addWidget(self.rtsp_name, 0, 1)

        rtsp_layout.addWidget(QLabel("协议:"), 1, 0)
        self.rtsp_protocol = QComboBox()
        self.rtsp_protocol.addItems(["rtsp://", "http://", "https://"])
        rtsp_layout.addWidget(self.rtsp_protocol, 1, 1)

        rtsp_layout.addWidget(QLabel("用户名:"), 2, 0)
        self.rtsp_user = QLineEdit()
        self.rtsp_user.setPlaceholderText("选填，如 admin")
        rtsp_layout.addWidget(self.rtsp_user, 2, 1)

        rtsp_layout.addWidget(QLabel("密码:"), 2, 2)
        self.rtsp_pass = QLineEdit()
        self.rtsp_pass.setPlaceholderText("选填")
        self.rtsp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        rtsp_layout.addWidget(self.rtsp_pass, 2, 3)

        rtsp_layout.addWidget(QLabel("地址:"), 3, 0)
        self.rtsp_host = QLineEdit()
        self.rtsp_host.setPlaceholderText("IP:端口/路径，如 192.168.1.100:554/stream1")
        rtsp_layout.addWidget(self.rtsp_host, 3, 1, 1, 3)

        rtsp_btn_row = QHBoxLayout()
        self.lbl_rtsp_preview = QLabel("")
        self.lbl_rtsp_preview.setStyleSheet("color: #6b7280; font-size: 11px;")
        rtsp_btn_row.addWidget(self.lbl_rtsp_preview, stretch=1)
        btn_rtsp_add = QPushButton("添加到列表")
        btn_rtsp_add.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold;")
        btn_rtsp_add.clicked.connect(self._add_rtsp_camera)
        rtsp_btn_row.addWidget(btn_rtsp_add)
        rtsp_layout.addLayout(rtsp_btn_row, 4, 0, 1, 4)

        # RTSP 输入变化时实时预览 URL
        for w in (self.rtsp_protocol, ):
            w.currentTextChanged.connect(self._update_rtsp_preview)
        for w in (self.rtsp_user, self.rtsp_pass, self.rtsp_host):
            w.textChanged.connect(self._update_rtsp_preview)

        add_tabs.addTab(tab_rtsp, "网络摄像头 (RTSP)")

        # Tab 3: 局域网扫描
        tab_scan = QWidget()
        scan_layout = QVBoxLayout(tab_scan)
        scan_layout.setContentsMargins(8, 8, 8, 8)

        scan_top = QHBoxLayout()
        self.btn_net_scan = QPushButton("扫描局域网设备")
        self.btn_net_scan.clicked.connect(self._scan_network)
        self.lbl_net_scan = QLabel("扫描本网段中开放摄像头端口 (554/8554/80) 的设备")
        self.lbl_net_scan.setStyleSheet("color: #9ca3af; font-size: 11px;")
        scan_top.addWidget(self.btn_net_scan)
        scan_top.addWidget(self.lbl_net_scan, stretch=1)
        scan_layout.addLayout(scan_top)

        self._net_device_layout = QVBoxLayout()
        self._net_device_buttons: list[QWidget] = []
        scan_layout.addLayout(self._net_device_layout)
        scan_layout.addStretch()
        add_tabs.addTab(tab_scan, "局域网扫描")

        # Tab 4: 视频文件
        tab_file = QWidget()
        file_layout = QHBoxLayout(tab_file)
        file_layout.setContentsMargins(8, 8, 8, 8)
        btn_add_file = QPushButton("选择视频文件")
        btn_add_file.clicked.connect(self._add_video_file)
        self.lbl_file = QLabel("支持 mp4 / avi 格式")
        self.lbl_file.setStyleSheet("color: #9ca3af;")
        file_layout.addWidget(btn_add_file)
        file_layout.addWidget(self.lbl_file, stretch=1)
        add_tabs.addTab(tab_file, "视频文件")

        layout.addWidget(add_tabs)

        # ============ 中部：摄像头列表 ============
        list_header = QHBoxLayout()
        list_header.addWidget(QLabel("已配置的摄像头:"))
        list_header.addStretch()
        lbl_count = QLabel()
        self._lbl_count = lbl_count
        list_header.addWidget(lbl_count)
        layout.addLayout(list_header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "地址/来源", "状态"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.currentCellChanged.connect(self._on_row_changed)
        layout.addWidget(self.table, stretch=1)

        # ============ 底部：操作按钮 + 预览 ============
        bottom = QHBoxLayout()

        # 预览区
        preview_group = QGroupBox("画面预览")
        preview_layout = QVBoxLayout()
        self.preview = PreviewWidget()
        preview_layout.addWidget(self.preview)
        preview_btn_row = QHBoxLayout()
        btn_preview = QPushButton("预览")
        btn_preview.clicked.connect(self._preview_selected)
        btn_stop_preview = QPushButton("停止")
        btn_stop_preview.clicked.connect(self.preview.clear_preview)
        preview_btn_row.addWidget(btn_preview)
        preview_btn_row.addWidget(btn_stop_preview)
        preview_layout.addLayout(preview_btn_row)
        preview_group.setLayout(preview_layout)
        bottom.addWidget(preview_group)

        # 操作按钮区
        ops_layout = QVBoxLayout()
        btn_remove = QPushButton("删除选中")
        btn_remove.clicked.connect(self.remove_selected)
        btn_test = QPushButton("测试连接")
        btn_test.clicked.connect(self.test_selected)
        btn_move_up = QPushButton("上移")
        btn_move_up.clicked.connect(self._move_up)
        btn_move_down = QPushButton("下移")
        btn_move_down.clicked.connect(self._move_down)
        ops_layout.addWidget(btn_remove)
        ops_layout.addWidget(btn_test)
        ops_layout.addWidget(btn_move_up)
        ops_layout.addWidget(btn_move_down)
        ops_layout.addStretch()

        btn_save = QPushButton("保存并应用")
        btn_save.setFixedHeight(42)
        btn_save.setStyleSheet("background-color: #16a34a; color: white; font-weight: bold; font-size: 13px;")
        btn_save.clicked.connect(self.save)
        ops_layout.addWidget(btn_save)

        bottom.addLayout(ops_layout)
        layout.addLayout(bottom)

        self.load_cameras(cameras)
        self._update_count()

    # ---------- 数据加载 ----------

    def load_cameras(self, cameras: list[dict]) -> None:
        self.table.setRowCount(0)
        for cam in cameras:
            self._insert_camera(cam)
        self._update_count()

    def _insert_camera(self, cam: dict) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(cam.get("id", ""))))
        self.table.setItem(row, 1, QTableWidgetItem(str(cam.get("name", ""))))
        self.table.setItem(row, 2, QTableWidgetItem(str(cam.get("source", ""))))
        status = QTableWidgetItem("未测试")
        status.setForeground(Qt.GlobalColor.gray)
        self.table.setItem(row, 3, status)

    def _update_count(self):
        self._lbl_count.setText(f"共 {self.table.rowCount()} 个")

    # ---------- 本地摄像头检测 ----------

    def _detect_cameras(self):
        self.btn_detect.setEnabled(False)
        self.lbl_detect_status.setText("正在扫描...")
        # 清除旧按钮
        for btn in self._local_buttons:
            btn.deleteLater()
        self._local_buttons.clear()

        # 后台检测
        def _run():
            found = detect_local_cameras()
            # 回到主线程更新 UI
            QTimer.singleShot(0, lambda: self._on_detect_done(found))

        Thread(target=_run, daemon=True).start()

    def _on_detect_done(self, found: list[dict]):
        self.btn_detect.setEnabled(True)
        if not found:
            self.lbl_detect_status.setText("未检测到本地摄像头")
            return
        self.lbl_detect_status.setText(f"检测到 {len(found)} 个摄像头，点击按钮一键添加:")
        for cam_info in found:
            idx = cam_info["index"]
            res = cam_info["resolution"]
            btn = QPushButton(f"摄像头 {idx}  ({res})")
            btn.clicked.connect(lambda checked, i=idx, r=res: self._add_local_camera(i, r))
            self.local_cam_list.addWidget(btn)
            self._local_buttons.append(btn)

    def _add_local_camera(self, index: int, resolution: str):
        # 检查是否已存在
        for row in range(self.table.rowCount()):
            src = self.table.item(row, 2)
            if src and src.text().strip() == str(index):
                QMessageBox.information(self, "提示", f"摄像头 {index} 已在列表中")
                return
        row = self.table.rowCount()
        cam_id = f"cam{row + 1:02d}"
        self._insert_camera({
            "id": cam_id,
            "name": f"本地摄像头-{index} ({resolution})",
            "source": index,
        })
        self._update_count()

    # ---------- RTSP 辅助 ----------

    def _build_rtsp_url(self) -> str:
        protocol = self.rtsp_protocol.currentText()
        user = self.rtsp_user.text().strip()
        pwd = self.rtsp_pass.text().strip()
        host = self.rtsp_host.text().strip()
        if not host:
            return ""
        auth = ""
        if user:
            auth = f"{user}:{pwd}@" if pwd else f"{user}@"
        return f"{protocol}{auth}{host}"

    def _update_rtsp_preview(self):
        url = self._build_rtsp_url()
        if url:
            self.lbl_rtsp_preview.setText(f"完整地址: {url}")
        else:
            self.lbl_rtsp_preview.setText("")

    def _add_rtsp_camera(self):
        url = self._build_rtsp_url()
        if not url or not self.rtsp_host.text().strip():
            QMessageBox.warning(self, "提示", "请填写摄像头地址")
            return
        name = self.rtsp_name.text().strip()
        if not name:
            name = self.rtsp_host.text().strip().split("/")[0]
        row = self.table.rowCount()
        cam_id = f"cam{row + 1:02d}"
        self._insert_camera({"id": cam_id, "name": name, "source": url})
        self._update_count()
        # 清空输入
        self.rtsp_name.clear()
        self.rtsp_user.clear()
        self.rtsp_pass.clear()
        self.rtsp_host.clear()

    # ---------- 局域网扫描 ----------

    def _scan_network(self):
        self.btn_net_scan.setEnabled(False)
        self.lbl_net_scan.setText("正在扫描局域网（约 10~30 秒）...")
        # 清除旧结果
        for w in self._net_device_buttons:
            w.deleteLater()
        self._net_device_buttons.clear()

        def _run():
            from core.network_scanner import scan_subnet, get_local_ip
            local_ip = get_local_ip()
            found = scan_subnet(timeout=0.3, max_workers=80)
            QTimer.singleShot(0, lambda: self._on_net_scan_done(found, local_ip))

        Thread(target=_run, daemon=True).start()

    def _on_net_scan_done(self, found: list[dict], local_ip: str):
        self.btn_net_scan.setEnabled(True)
        if not found:
            self.lbl_net_scan.setText(
                f"未发现局域网摄像头设备（本机 IP: {local_ip or '未知'}）"
            )
            return
        self.lbl_net_scan.setText(
            f"发现 {len(found)} 个设备（本机: {local_ip}），点击添加:"
        )
        for dev in found:
            ip = dev["ip"]
            hostname = dev.get("hostname", "")
            ports = dev.get("ports", [])
            urls = dev.get("urls", [])
            port_str = ", ".join(str(p) for p in ports)
            label_text = f"{ip}  (端口: {port_str})"
            if hostname:
                label_text = f"{ip} [{hostname}]  (端口: {port_str})"

            row_widget = QWidget()
            row_lay = QHBoxLayout(row_widget)
            row_lay.setContentsMargins(0, 2, 0, 2)
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 11px;")
            row_lay.addWidget(lbl, stretch=1)

            for url in urls:
                btn = QPushButton(f"添加 {url.split('://')[0]}")
                btn.setFixedWidth(100)
                btn.clicked.connect(
                    lambda checked, u=url, h=hostname, i=ip: self._add_net_device(i, h, u)
                )
                row_lay.addWidget(btn)

            self._net_device_layout.addWidget(row_widget)
            self._net_device_buttons.append(row_widget)

    def _add_net_device(self, ip: str, hostname: str, url: str):
        name = hostname if hostname else ip
        row = self.table.rowCount()
        cam_id = f"cam{row + 1:02d}"
        self._insert_camera({"id": cam_id, "name": name, "source": url})
        self._update_count()

    # ---------- 视频文件 ----------

    def _add_video_file(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "Videos (*.mp4 *.avi *.mkv *.mov)"
        )
        if not path:
            return
        import os
        name = os.path.splitext(os.path.basename(path))[0]
        row = self.table.rowCount()
        cam_id = f"cam{row + 1:02d}"
        self._insert_camera({"id": cam_id, "name": name, "source": path})
        self._update_count()
        self.lbl_file.setText(f"已添加: {os.path.basename(path)}")

    # ---------- 列表操作 ----------

    def remove_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            QMessageBox.information(self, "提示", "请先选中要删除的行")
            return
        for row in rows:
            self.table.removeRow(row)
        self._update_count()

    def _move_up(self):
        row = self.table.currentRow()
        if row <= 0:
            return
        self._swap_rows(row, row - 1)
        self.table.setCurrentCell(row - 1, 0)

    def _move_down(self):
        row = self.table.currentRow()
        if row < 0 or row >= self.table.rowCount() - 1:
            return
        self._swap_rows(row, row + 1)
        self.table.setCurrentCell(row + 1, 0)

    def _swap_rows(self, r1: int, r2: int):
        for col in range(self.table.columnCount()):
            item1 = self.table.item(r1, col)
            item2 = self.table.item(r2, col)
            t1 = item1.text() if item1 else ""
            t2 = item2.text() if item2 else ""
            self.table.setItem(r1, col, QTableWidgetItem(t2))
            self.table.setItem(r2, col, QTableWidgetItem(t1))

    def _on_row_changed(self, row, col, prev_row, prev_col):
        pass  # 可扩展：自动预览选中行

    # ---------- 测试 & 预览 ----------

    def test_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "提示", "请先选中要测试的摄像头")
            return
        row = rows[0]
        source_item = self.table.item(row, 2)
        if source_item is None:
            return
        source_raw = source_item.text()
        source = normalize_source(source_raw)
        cap = cv2.VideoCapture(source)
        ok = cap.isOpened()
        if ok:
            ret, _ = cap.read()
            ok = ret
        cap.release()
        status_item = self.table.item(row, 3)
        if ok:
            if status_item:
                status_item.setText("可用")
                status_item.setForeground(Qt.GlobalColor.green)
            QMessageBox.information(self, "测试成功", f"摄像头可正常连接")
        else:
            if status_item:
                status_item.setText("不可用")
                status_item.setForeground(Qt.GlobalColor.red)
            QMessageBox.warning(self, "测试失败", f"无法打开: {source_raw}\n\n请检查地址是否正确、设备是否在线")

    def _preview_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "提示", "请先选中要预览的摄像头")
            return
        source_item = self.table.item(rows[0], 2)
        if source_item is None:
            return
        source = normalize_source(source_item.text())
        self.preview.start(source)

    # ---------- 保存 ----------

    def save(self) -> None:
        cameras = []
        for row in range(self.table.rowCount()):
            id_item = self.table.item(row, 0)
            name_item = self.table.item(row, 1)
            source_item = self.table.item(row, 2)
            if not id_item or not source_item:
                continue
            cam_id = id_item.text().strip()
            if not cam_id:
                continue
            name = name_item.text().strip() if name_item else cam_id
            source = normalize_source(source_item.text())
            cameras.append({"id": cam_id, "name": name, "source": source})

        if not cameras:
            QMessageBox.warning(self, "提示", "至少需要添加一个摄像头")
            return

        save_cameras(self.config_path, cameras)
        QMessageBox.information(
            self, "保存成功",
            f"已保存 {len(cameras)} 个摄像头配置。\n重启程序后生效。"
        )
        parent = self.parent()
        if parent and hasattr(parent, "load_cameras_from_manager"):
            parent.load_cameras_from_manager(cameras)

    def closeEvent(self, event):
        self.preview.stop()
        super().closeEvent(event)
