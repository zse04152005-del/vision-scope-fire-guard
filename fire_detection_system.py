import logging
import sys
import time
import os
from pathlib import Path
from threading import Lock
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel,
                             QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
                             QGroupBox, QFileDialog, QDialog, QLineEdit, QComboBox,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QGridLayout, QSpinBox, QSizePolicy, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QImage, QFont, QPixmap, QKeySequence, QShortcut
from ultralytics import YOLO
from ui_components import (
    build_grid_positions,
    build_scroll_area,
    compute_available_grid_width,
    compute_grid_cols,
    compute_grid_min_size,
    resolve_grid_cols,
    CAM_TILE_MIN_W,
    CAM_TILE_MIN_H,
    CameraTile,
)
from config_loader import load_config
from alarm_logic import AlarmTracker
from capture_worker import CameraWorker
from event_logger import write_event
from alarm_saver import save_alarm_images
from camera_manager import CameraManager
from alert_flash import AlertFlashState
from alert_beep import AlertBeepState
from camera_config_utils import save_cameras
from ui_utils import reorder_camera_order, filter_alarm_events
from logging_setup import setup_logging
from notifier import AlarmNotifier
from system_monitor import SystemMonitor
from ui_theme import build_qss, get_theme
from ui_toast import ToastManager
from alarm_exporter import export_alarm_events_csv

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
WINDOW_TITLE = "校园多路火警监控系统"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1200, 760)
        self.config = self.load_config_safe()
        self.cameras = self.config.get("cameras", [])
        self.grid_cols_cfg = self.config.get("grid_cols")
        if not self.cameras:
            self.cameras = [
                {"id": f"cam{i+1:02d}", "name": f"Cam{i+1:02d}", "source": i}
                for i in range(12)
            ]
        self.camera_order = [cam.get("id", f"cam{i+1:02d}") for i, cam in enumerate(self.cameras)]
        self.primary_cam_id = self.camera_order[0] if self.camera_order else ""

        alarm_cfg = self.config.get("alarm", {})
        self.conf_threshold = float(alarm_cfg.get("conf_threshold", 0.5))
        self.hit_threshold = int(alarm_cfg.get("hit_threshold", 3))
        self.cooldown_seconds = int(alarm_cfg.get("cooldown_seconds", 10))
        self.interval_s = float(alarm_cfg.get("interval_s", 0.2))

        perf_cfg = self.config.get("perf", {}) or {}
        max_fps = float(perf_cfg.get("max_fps", 0) or 0)
        if max_fps > 0:
            self.interval_s = max(self.interval_s, 1.0 / max_fps)
        self.infer_size = int(perf_cfg.get("infer_size", 0) or 0)
        self.heartbeat_timeout = float(perf_cfg.get("heartbeat_timeout", 5.0) or 0)

        self.model_path = BASE_DIR / self.config.get("model_path", "best.pt")
        self.output_dir = BASE_DIR / self.config.get("output_dir", "results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.alarm_dir = self.output_dir / "alarms"
        self.alarm_dir.mkdir(parents=True, exist_ok=True)
        self.event_log_path = self.output_dir / "events.csv"
        setup_logging(str(self.output_dir), self.config.get("logging", {}))
        self.notifier = AlarmNotifier(self.config.get("webhook", {}))
        self.system_monitor = SystemMonitor()
        self.theme_name = str(self.config.get("theme", "dark")).lower()
        self.theme = get_theme(self.theme_name)
        self.toasts = None

        try:
            if not self.model_path.exists():
                raise FileNotFoundError(f"模型文件不存在: {self.model_path}")
            self.model = YOLO(str(self.model_path))
        except Exception as e:
            QMessageBox.critical(
                None,
                "模型加载失败",
                f"无法加载 YOLO 模型：\n{self.model_path}\n\n错误信息：\n{e}",
            )
            raise SystemExit(1)
        self.model_lock = Lock()
        self.alarm_tracker = AlarmTracker(self.hit_threshold, self.cooldown_seconds)
        self.alert_count = 0
        self.workers = {}
        self.online_cams = set()
        self.paused = False
        self.latest_results = {}
        self.alarm_events = []
        self.camera_manager = None
        self.alert_timer = QTimer(self)
        self.alert_timer.setInterval(300)
        self.alert_timer.timeout.connect(self.on_alert_flash_tick)
        self.alert_flash_state = AlertFlashState(0)
        self.beep_timer = QTimer(self)
        self.beep_timer.setInterval(700)
        self.beep_timer.timeout.connect(self.on_beep_tick)
        self.beep_state = AlertBeepState(0)
        self.shortcut_fullscreen = QShortcut(QKeySequence("F11"), self)
        self.shortcut_fullscreen.activated.connect(self.toggle_fullscreen)
        self.zoom_dialog = None
        self.zoom_label = None
        self.zoom_cam_id = None
        self.filtered_alarm_events = []

        self.setup_ui()
        self.setup_styles()
        self.toasts = ToastManager(self)

        self.sys_timer = QTimer(self)
        self.sys_timer.setInterval(2000)
        self.sys_timer.timeout.connect(self.refresh_system_stats)
        self.sys_timer.start()
        self.refresh_system_stats()

    def load_config_safe(self) -> dict:
        try:
            return load_config(str(CONFIG_PATH))
        except Exception as e:
            logger.exception("配置加载失败: %s", e)
            return {}

    def setup_ui(self):
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        root_layout = QVBoxLayout(self.main_widget)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)
        self.main_widget.setStyleSheet("border: 4px solid transparent;")

        # 顶部状态栏
        status_bar = QHBoxLayout()
        title_label = QLabel(WINDOW_TITLE)
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self.lbl_online = QLabel(f"在线: 0/{len(self.cameras)}")
        self.lbl_alerts = QLabel("今日告警: 0")
        self.lbl_gpu = QLabel("CPU: - | 内存: - | GPU: -")
        self.lbl_net = QLabel("网络: 正常")
        self.lbl_time = QLabel("时间: --:--")
        status_bar.addWidget(title_label)
        status_bar.addStretch()
        status_bar.addWidget(self.lbl_online)
        status_bar.addWidget(self.lbl_alerts)
        status_bar.addWidget(self.lbl_gpu)
        status_bar.addWidget(self.lbl_net)
        status_bar.addWidget(self.lbl_time)
        status_container = QWidget()
        status_container.setLayout(status_bar)
        root_layout.addWidget(status_container)

        # 主体区域
        body_layout = QHBoxLayout()
        root_layout.addLayout(body_layout, stretch=1)

        # 左侧：多路网格（可滚动）
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(6)
        self.camera_tiles = []
        self.tile_by_id = {}
        self.grid_count = max(12, len(self.cameras))
        right_width = 320
        available_width = compute_available_grid_width(self.width(), right_width, 80)
        self.grid_cols = resolve_grid_cols(
            config_cols=self.grid_cols_cfg,
            available_width=available_width,
            tile_w=CAM_TILE_MIN_W,
            spacing=self.grid_layout.spacing(),
            max_cols=4,
        )
        self.build_grid()
        self.grid_scroll = build_scroll_area(self.grid_container)
        body_layout.addWidget(self.grid_scroll, stretch=7)

        # 右侧：控制 + 信息 + 告警中心
        right_panel = QVBoxLayout()

        gb_source = QGroupBox("视频源控制")
        layout_source = QGridLayout()
        self.btn_open_cam = QPushButton("▶  启动全部")
        self.btn_stop = QPushButton("■  停止全部")
        self.btn_open_cam.clicked.connect(self.start_all)
        self.btn_stop.clicked.connect(self.stop_all)
        layout_source.addWidget(self.btn_open_cam, 0, 0)
        layout_source.addWidget(self.btn_stop, 0, 1)

        self.btn_video = QPushButton("▤  导入视频")
        self.btn_img = QPushButton("▦  导入图片")
        self.btn_video.clicked.connect(self.select_video)
        self.btn_img.clicked.connect(self.select_image)
        layout_source.addWidget(self.btn_video, 1, 0)
        layout_source.addWidget(self.btn_img, 1, 1)

        self.btn_pause = QPushButton("‖  暂停全部")
        self.btn_pause.clicked.connect(self.toggle_pause)
        layout_source.addWidget(self.btn_pause, 2, 0, 1, 2)
        self.btn_manage = QPushButton("⚙  摄像头管理")
        self.btn_manage.clicked.connect(self.open_camera_manager)
        layout_source.addWidget(self.btn_manage, 3, 0, 1, 2)
        self.btn_theme = QPushButton("切换浅色" if self.theme_name == "dark" else "切换深色")
        self.btn_theme.clicked.connect(self.toggle_theme)
        layout_source.addWidget(self.btn_theme, 4, 0, 1, 2)
        gb_source.setLayout(layout_source)
        right_panel.addWidget(gb_source)

        gb_param = QGroupBox("参数调节")
        layout_param = QVBoxLayout()
        row_conf = QHBoxLayout()
        row_conf.addWidget(QLabel("置信度:"))
        self.conf_spin = QSpinBox()
        self.conf_spin.setRange(0, 100)
        self.conf_spin.setValue(50)
        row_conf.addWidget(self.conf_spin)
        layout_param.addLayout(row_conf)
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(0, 100)
        self.conf_slider.setValue(50)
        self.conf_slider.valueChanged.connect(self.update_conf)
        layout_param.addWidget(self.conf_slider)
        gb_param.setLayout(layout_param)
        right_panel.addWidget(gb_param)

        gb_info = QGroupBox("实时信息")
        layout_info = QVBoxLayout()
        self.lbl_status = QLabel("状态: 待机")
        self.lbl_fps = QLabel("用时: 0.00s")
        self.lbl_count = QLabel("目标数: 0")
        self.lbl_conf_large = QLabel("0.00%")
        self.lbl_conf_large.setStyleSheet(
            f"font-size: 24px; color: {self.theme.primary}; font-weight: bold;"
        )
        self.lbl_conf_large.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_info.addWidget(self.lbl_status)
        layout_info.addWidget(self.lbl_fps)
        layout_info.addWidget(self.lbl_count)
        layout_info.addWidget(QLabel("最高置信度:"))
        layout_info.addWidget(self.lbl_conf_large)
        gb_info.setLayout(layout_info)
        right_panel.addWidget(gb_info)

        gb_detail = QGroupBox("检测详情")
        detail_layout = QVBoxLayout()
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["序号", "类别", "置信度", "坐标"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.result_table.setFixedHeight(160)
        detail_layout.addWidget(self.result_table)
        gb_detail.setLayout(detail_layout)
        right_panel.addWidget(gb_detail)

        gb_alarm = QGroupBox("告警中心")
        alarm_layout = QVBoxLayout()
        filter_row = QHBoxLayout()
        self.alarm_search = QLineEdit()
        self.alarm_search.setPlaceholderText("搜索摄像头/时间")
        self.alarm_level = QComboBox()
        self.alarm_level.addItems(["all", "confirm", "warn"])
        self.alarm_search.textChanged.connect(self.refresh_alarm_table)
        self.alarm_level.currentTextChanged.connect(self.refresh_alarm_table)
        filter_row.addWidget(self.alarm_search)
        filter_row.addWidget(self.alarm_level)
        self.btn_export = QPushButton("导出")
        self.btn_export.clicked.connect(self.export_alarms)
        filter_row.addWidget(self.btn_export)
        alarm_layout.addLayout(filter_row)
        self.alarm_table = QTableWidget()
        self.alarm_table.setColumnCount(4)
        self.alarm_table.setHorizontalHeaderLabels(["时间", "摄像头", "等级", "状态"])
        self.alarm_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.alarm_table.setFixedHeight(220)
        self.alarm_table.cellDoubleClicked.connect(self.open_alarm_detail)
        alarm_layout.addWidget(self.alarm_table)
        gb_alarm.setLayout(alarm_layout)
        right_panel.addWidget(gb_alarm)

        right_panel.addStretch()

        row_btns = QHBoxLayout()
        btn_snap = QPushButton("◉  保存截图")
        btn_snap.setStyleSheet(
            f"background-color: {self.theme.danger}; color: #ffffff; font-weight: bold; border: none;"
        )
        btn_snap.clicked.connect(self.save_screenshot)
        btn_snap.setFixedHeight(42)
        row_btns.addWidget(btn_snap)
        right_panel.addLayout(row_btns)

        container_right = QWidget()
        container_right.setLayout(right_panel)
        container_right.setFixedWidth(320)
        self.right_scroll = build_scroll_area(container_right, always_show_vertical=True)
        self.right_scroll.setFixedWidth(330)
        body_layout.addWidget(self.right_scroll)

        self.primary_cam_id = self.camera_order[0]
        self.primary_tile = self.tile_by_id[self.primary_cam_id]

    def setup_styles(self):
        self.setStyleSheet(build_qss(self.theme))
        border_color = self.theme.border
        self.main_widget.setStyleSheet(f"border: 4px solid transparent;")
        # 保存按钮保持告警红强调色
        try:
            self.lbl_conf_large.setStyleSheet(
                f"font-size: 24px; color: {self.theme.primary}; font-weight: bold;"
            )
        except Exception:
            pass

    def toggle_theme(self):
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.theme = get_theme(self.theme_name)
        self.setup_styles()
        try:
            self.btn_theme.setText(("切换浅色" if self.theme_name == "dark" else "切换深色"))
        except Exception:
            pass
        self._save_theme_to_config()
        if self.toasts:
            self.toasts.show(f"已切换至{'深色' if self.theme_name == 'dark' else '浅色'}主题", level="info")

    def _save_theme_to_config(self):
        try:
            import json
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["theme"] = self.theme_name
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.debug("写入主题配置失败: %s", exc)

    def build_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self.camera_tiles = []
        self.empty_tiles = []
        positions = build_grid_positions(self.grid_count, cols=self.grid_cols)
        id_to_cam = {cam.get("id"): cam for cam in self.cameras}
        for i, (row, col) in enumerate(positions):
            if i < len(self.camera_order):
                cam_id = self.camera_order[i]
                cam = id_to_cam.get(cam_id, {})
                name = cam.get("name", cam_id)
                tile = self.tile_by_id.get(cam_id)
                if tile is None:
                    tile = CameraTile(name)
                    self.tile_by_id[cam_id] = tile
                    tile.swapRequested.connect(self.on_swap_requested)
                    tile.zoomRequested.connect(self.open_zoom_view)
                tile.cam_id = cam_id
                tile.name_label.setText(name)
                self.camera_tiles.append(tile)
                self.grid_layout.addWidget(tile, row, col)
            else:
                tile = CameraTile(f"Cam{i+1:02d}")
                tile.cam_id = ""
                tile.set_status("EMPTY", "#bbb")
                self.empty_tiles.append(tile)
                self.grid_layout.addWidget(tile, row, col)
        rows = (self.grid_count + self.grid_cols - 1) // self.grid_cols
        grid_min = compute_grid_min_size(
            tile_w=CAM_TILE_MIN_W,
            tile_h=CAM_TILE_MIN_H,
            rows=rows,
            cols=self.grid_cols,
            spacing=self.grid_layout.spacing(),
        )
        self.grid_container.setMinimumSize(grid_min)
        if self.primary_cam_id and self.primary_cam_id in self.tile_by_id:
            self.primary_tile = self.tile_by_id[self.primary_cam_id]

    # --- 功能逻辑 ---

    def start_all(self):
        self.stop_all(clear_tables=False)
        self.paused = False
        self.btn_pause.setText("暂停全部")
        self.lbl_status.setText("启动中...")
        for cam in self.cameras:
            self.start_worker_for(cam)

    def select_video(self):
        self.stop_all(clear_tables=False)
        file_path, _ = QFileDialog.getOpenFileName(self, "选择视频", "", "Videos (*.mp4 *.avi)")
        if file_path:
            cam = {"id": self.primary_cam_id, "name": self.primary_tile.name_label.text(), "source": file_path}
            self.start_worker_for(cam)
            self.lbl_status.setText("正在播放视频(主画面)...")

    def select_image(self):
        self.stop_all(clear_tables=False)
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.jpg *.png)")
        if file_path:
            results = self.model(file_path)[0]
            qt_img = CameraWorker.convert_cv_qt(results.plot())
            self.primary_tile.set_frame(qt_img)
            self.update_primary_details(results, 0.0)
            self.latest_results[self.primary_cam_id] = results
            max_conf = 0.0
            if len(results.boxes) > 0:
                max_conf = max(float(box.conf) for box in results.boxes)
            self.lbl_count.setText(f"目标数: {len(results.boxes)}")
            self.lbl_conf_large.setText(f"{max_conf*100:.1f}%")
            if max_conf >= self.conf_threshold and len(results.boxes) > 0:
                ts = time.time()
                orig_path, ann_path = self.save_alarm_images_for(self.primary_cam_id, ts)
                event = {
                    "camera": self.primary_cam_id,
                    "level": "confirm",
                    "ts": ts,
                    "orig_path": orig_path,
                    "annotated_path": ann_path,
                }
                self.add_alarm_event(event)
            self.lbl_status.setText("图片检测完成")
            self.primary_tile.set_status("IMAGE", "#666")

    def stop_all(self, clear_tables: bool = True):
        for worker in self.workers.values():
            if worker.isRunning():
                worker.stop()
        self.workers = {}
        self.online_cams = set()
        self.update_online_label()
        self.paused = False
        self.btn_pause.setText("‖  暂停全部")
        for tile in self.tile_by_id.values():
            tile.video_label.clear()
            tile.video_label.setText("已停止")
            tile.set_status("OFFLINE", "#999")
            tile.meta_label.setText("FPS: 0  |  目标: 0")
        self.lbl_status.setText("待机")
        if clear_tables:
            self.result_table.setRowCount(0)
            self.alarm_table.setRowCount(0)

    def toggle_pause(self):
        self.paused = not self.paused
        for worker in self.workers.values():
            worker.set_paused(self.paused)
        if self.paused:
            self.btn_pause.setText("▶  继续全部")
            self.lbl_status.setText("已暂停")
        else:
            self.btn_pause.setText("‖  暂停全部")
            self.lbl_status.setText("运行中")

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def on_swap_requested(self, source_id: str, target_id: str):
        new_order = reorder_camera_order(self.camera_order, source_id, target_id)
        if new_order == self.camera_order:
            return
        self.camera_order = new_order
        id_to_cam = {cam.get("id"): cam for cam in self.cameras}
        self.cameras = [id_to_cam[cid] for cid in self.camera_order if cid in id_to_cam]
        save_cameras(str(CONFIG_PATH), self.cameras)
        self.build_grid()

    def update_conf(self):
        val = self.conf_slider.value()
        self.conf_spin.setValue(val)
        self.conf_threshold = val / 100.0
        for worker in self.workers.values():
            worker.conf_threshold = self.conf_threshold

    def start_worker_for(self, cam: dict) -> None:
        cam_id = cam.get("id")
        source = cam.get("source")
        if not cam_id:
            return
        existing = self.workers.get(cam_id)
        if existing and existing.isRunning():
            return
        worker = CameraWorker(
            cam_id=cam_id,
            source=source,
            model=self.model,
            model_lock=self.model_lock,
            conf_threshold=self.conf_threshold,
            interval_s=self.interval_s,
            infer_size=self.infer_size,
            heartbeat_timeout=self.heartbeat_timeout,
        )
        worker.frame_signal.connect(self.on_frame)
        worker.result_signal.connect(self.on_result)
        worker.hit_signal.connect(self.on_hit)
        worker.status_signal.connect(self.on_status)
        worker.error_signal.connect(self.on_worker_error)
        self.workers[cam_id] = worker
        worker.start()

    def on_frame(self, cam_id: str, qt_img: QImage, inference_time: float, count: int, max_conf: float):
        tile = self.tile_by_id.get(cam_id)
        if tile:
            tile.set_frame(qt_img)
            fps = 0 if inference_time <= 0 else int(1.0 / inference_time)
            tile.meta_label.setText(f"FPS: {fps}  |  目标: {count}")
            tile.set_status("ONLINE", self.theme.success)

        if cam_id == self.primary_cam_id:
            self.lbl_fps.setText(f"用时: {inference_time:.3f}s")
            self.lbl_count.setText(f"目标数: {count}")
            self.lbl_conf_large.setText(f"{max_conf*100:.1f}%")
        self.update_zoom_view(cam_id, qt_img)

    def on_result(self, cam_id: str, results, inference_time: float):
        self.latest_results[cam_id] = results
        if cam_id == self.primary_cam_id:
            self.update_primary_details(results, inference_time)

    def update_primary_details(self, results, inference_time: float):
        self.result_table.setRowCount(0)
        if len(results.boxes) == 0:
            return
        for i, box in enumerate(results.boxes):
            self.result_table.insertRow(i)
            cls_id = int(box.cls[0])
            coords = box.xyxy[0].cpu().numpy().astype(int)
            self.result_table.setItem(i, 0, QTableWidgetItem(str(i+1)))
            self.result_table.setItem(i, 1, QTableWidgetItem(results.names[cls_id]))
            self.result_table.setItem(i, 2, QTableWidgetItem(f"{float(box.conf):.2f}"))
            self.result_table.setItem(i, 3, QTableWidgetItem(str(coords)))

    def on_hit(self, cam_id: str, hit: bool, ts: float):
        event = self.alarm_tracker.update(cam_id, hit, ts)
        if event:
            orig_path, ann_path = self.save_alarm_images_for(cam_id, ts)
            event["orig_path"] = orig_path
            event["annotated_path"] = ann_path
            self.add_alarm_event(event)

    def add_alarm_event(self, event: dict):
        self.alert_count += 1
        self.lbl_alerts.setText(f"今日告警: {self.alert_count}")
        ts_str = time.strftime("%H:%M:%S", time.localtime(event["ts"]))
        event_record = {
            "ts": event["ts"],
            "time": ts_str,
            "camera": event["camera"],
            "level": event["level"],
            "status": "pending",
            "orig_path": event.get("orig_path"),
            "annotated_path": event.get("annotated_path"),
        }
        write_event(str(self.event_log_path), event_record)
        self.notify_event(event_record)
        self.alarm_events.append(event_record)
        self.refresh_alarm_table()
        self.trigger_alert_visual()
        self.highlight_camera(event["camera"])

    def on_status(self, cam_id: str, status: str):
        tile = self.tile_by_id.get(cam_id)
        if tile:
            if status == "ONLINE":
                tile.set_status("ONLINE", self.theme.success)
            elif status == "RECONNECTING":
                tile.set_status("RECONNECTING", self.theme.warning)
            else:
                tile.set_status("OFFLINE", self.theme.text_muted)
        if status == "ONLINE":
            self.online_cams.add(cam_id)
        else:
            self.online_cams.discard(cam_id)
        self.update_online_label()

    def update_online_label(self):
        self.lbl_online.setText(f"在线: {len(self.online_cams)}/{len(self.cameras)}")

    def on_worker_error(self, cam_id: str, msg: str):
        tile = self.tile_by_id.get(cam_id)
        if tile:
            tile.set_status("OFFLINE", "#999")
        self.lbl_status.setText(f"{cam_id} 离线")
        logger.warning("%s 错误: %s", cam_id, msg)

    def save_alarm_images_for(self, cam_id: str, ts: float):
        results = self.latest_results.get(cam_id)
        if results is None:
            return None, None
        try:
            orig_img = results.orig_img
            annotated = results.plot()
            return save_alarm_images(str(self.alarm_dir), cam_id, ts, orig_img, annotated)
        except Exception as exc:
            logger.exception("保存告警截图失败: %s", exc)
            return None, None

    ALARM_TABLE_MAX_ROWS = 500

    def refresh_alarm_table(self):
        text = self.alarm_search.text() if hasattr(self, "alarm_search") else ""
        level = self.alarm_level.currentText() if hasattr(self, "alarm_level") else "all"
        self.filtered_alarm_events = filter_alarm_events(self.alarm_events, text, level)
        # 仅渲染最新 N 条，避免大数据量 QTableWidget 卡顿（完整数据仍在 filtered_alarm_events 中用于导出）
        visible = self.filtered_alarm_events[-self.ALARM_TABLE_MAX_ROWS:]
        self.alarm_table.setRowCount(0)
        for i, ev in enumerate(visible):
            self.alarm_table.insertRow(i)
            self.alarm_table.setItem(i, 0, QTableWidgetItem(ev.get("time", "")))
            self.alarm_table.setItem(i, 1, QTableWidgetItem(ev.get("camera", "")))
            self.alarm_table.setItem(i, 2, QTableWidgetItem(ev.get("level", "")))
            self.alarm_table.setItem(i, 3, QTableWidgetItem(ev.get("status", "")))
            if ev.get("level") == "confirm":
                for col in range(4):
                    item = self.alarm_table.item(i, col)
                    if item:
                        item.setBackground(Qt.GlobalColor.red)
                        item.setForeground(Qt.GlobalColor.white)

    def highlight_camera(self, cam_id: str):
        tile = self.tile_by_id.get(cam_id)
        if not tile:
            return
        tile.video_label.setStyleSheet(
            f"background-color: {self.theme.video_bg}; border: 3px solid {self.theme.danger}; border-radius: 6px;"
        )
        QTimer.singleShot(
            2000,
            lambda: tile.video_label.setStyleSheet(
                f"background-color: {self.theme.video_bg}; border: 1px solid {self.theme.tile_border}; border-radius: 6px;"
            ),
        )

    def open_alarm_detail(self, row: int, _col: int):
        visible = self.filtered_alarm_events[-self.ALARM_TABLE_MAX_ROWS:]
        if row >= len(visible):
            return
        event = visible[row]
        dialog = QDialog(self)
        dialog.setWindowTitle("告警详情")
        dialog.resize(720, 480)

        layout = QVBoxLayout(dialog)
        info = QLabel(
            f"时间: {event.get('time')}  |  摄像头: {event.get('camera')}  |  等级: {event.get('level')}"
        )
        layout.addWidget(info)

        img_row = QHBoxLayout()
        orig_label = QLabel("原图")
        ann_label = QLabel("标注图")
        orig_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ann_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        orig_path = event.get("orig_path")
        ann_path = event.get("annotated_path")
        if orig_path and os.path.exists(orig_path):
            orig_label.setPixmap(QPixmap(orig_path).scaled(340, 240, Qt.AspectRatioMode.KeepAspectRatio))
        if ann_path and os.path.exists(ann_path):
            ann_label.setPixmap(QPixmap(ann_path).scaled(340, 240, Qt.AspectRatioMode.KeepAspectRatio))
        img_row.addWidget(orig_label)
        img_row.addWidget(ann_label)
        layout.addLayout(img_row)
        dialog.exec()

    def open_zoom_view(self, cam_id: str):
        if self.zoom_dialog is None:
            self.zoom_dialog = QDialog(self)
            self.zoom_dialog.setWindowTitle("画面放大")
            self.zoom_dialog.resize(800, 600)
            layout = QVBoxLayout(self.zoom_dialog)
            self.zoom_label = QLabel()
            self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.zoom_label)
        self.zoom_cam_id = cam_id
        tile = self.tile_by_id.get(cam_id)
        if tile and tile.video_label.pixmap():
            self.zoom_label.setPixmap(tile.video_label.pixmap().scaled(760, 520, Qt.AspectRatioMode.KeepAspectRatio))
        self.zoom_dialog.show()
        self.zoom_dialog.raise_()
        self.zoom_dialog.activateWindow()

    def update_zoom_view(self, cam_id: str, qt_img: QImage):
        if self.zoom_dialog and self.zoom_dialog.isVisible() and self.zoom_cam_id == cam_id:
            self.zoom_label.setPixmap(QPixmap.fromImage(qt_img).scaled(760, 520, Qt.AspectRatioMode.KeepAspectRatio))

    def open_camera_manager(self):
        if self.camera_manager and self.camera_manager.isVisible():
            self.camera_manager.raise_()
            self.camera_manager.activateWindow()
            return
        self.camera_manager = CameraManager(self, str(CONFIG_PATH), self.cameras)
        self.camera_manager.setModal(False)
        self.camera_manager.show()

    def load_cameras_from_manager(self, cameras: list[dict]) -> None:
        self.cameras = cameras
        self.lbl_status.setText("摄像头配置已保存，重启后生效")

    def export_alarms(self) -> None:
        if not self.filtered_alarm_events:
            QMessageBox.information(self, "提示", "当前没有可导出的告警事件")
            return
        default_name = time.strftime("alarms_%Y%m%d_%H%M%S.csv")
        default_path = str(self.output_dir / default_name)
        path, _ = QFileDialog.getSaveFileName(self, "导出告警 CSV", default_path, "CSV (*.csv)")
        if not path:
            return
        try:
            n = export_alarm_events_csv(path, self.filtered_alarm_events)
        except Exception as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return
        if self.toasts:
            self.toasts.show(f"已导出 {n} 条告警至 {os.path.basename(path)}", level="success")

    def refresh_system_stats(self) -> None:
        try:
            stats = self.system_monitor.sample()
            self.lbl_gpu.setText(self.system_monitor.format_stats(stats))
        except Exception as exc:
            logger.debug("系统状态刷新失败: %s", exc)

    def notify_event(self, event: dict) -> None:
        logger.info("告警通知: %s", event)
        try:
            self.notifier.notify(event)
        except Exception as exc:
            logger.warning("webhook 通知异常: %s", exc)
        if self.toasts:
            self.toasts.show(
                f"火警告警 · {event.get('camera', '')} · {event.get('time', '')}",
                level="danger",
                duration_ms=4000,
            )

    def trigger_alert_visual(self):
        self.alert_flash_state = AlertFlashState(cycles=8)
        self.beep_state = AlertBeepState(beeps=10)
        if not self.alert_timer.isActive():
            self.alert_timer.start()
        if not self.beep_timer.isActive():
            self.beep_timer.start()

    def on_alert_flash_tick(self):
        color = self.alert_flash_state.next_color()
        if color is None:
            self.alert_timer.stop()
            self.main_widget.setStyleSheet("border: 4px solid transparent;")
            return
        self.main_widget.setStyleSheet(f"border: 4px solid {color};")

    def on_beep_tick(self):
        if self.beep_state.next_beep() is None:
            self.beep_timer.stop()
            return
        QApplication.beep()

    # ============ 修复后的截图功能 ============
    def save_screenshot(self):
        # 检查画面是否为空
        if not self.primary_tile.video_label.pixmap():
            QMessageBox.warning(self, "提示", "当前没有画面，无法截图！")
            return

        # 构造完整文件名
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        file_name = f"Result_{timestamp}.jpg"
        # 使用 os.path.join 拼接路径，防止斜杠问题
        full_path = os.path.join(str(self.output_dir), file_name)

        try:
            # 保存图片
            self.primary_tile.video_label.pixmap().save(full_path)
            logger.info("截图成功: %s", full_path)
            
            # 弹窗提示成功 (这样你不需要去文件夹看就知道成了没)
            QMessageBox.information(self, "保存成功", f"截图已保存至:\n{full_path}")
            
            self.lbl_status.setText(f"已截图: {file_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法写入文件:\n{str(e)}")
    # ========================================

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            if self.grid_cols_cfg:
                return
            right_width = 320
            avail = compute_available_grid_width(self.width(), right_width, 80)
            new_cols = resolve_grid_cols(
                config_cols=None,
                available_width=avail,
                tile_w=CAM_TILE_MIN_W,
                spacing=self.grid_layout.spacing(),
                max_cols=4,
            )
            if new_cols != self.grid_cols and new_cols > 0:
                self.grid_cols = new_cols
                self.build_grid()
        except Exception as exc:
            logger.debug("resize 重排失败: %s", exc)

    def closeEvent(self, event):
        try:
            if self.alert_timer.isActive():
                self.alert_timer.stop()
            if self.beep_timer.isActive():
                self.beep_timer.stop()
            if hasattr(self, "sys_timer") and self.sys_timer.isActive():
                self.sys_timer.stop()
        except Exception:
            pass
        self.stop_all(clear_tables=False)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
