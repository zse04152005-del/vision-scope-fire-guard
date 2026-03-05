import cv2
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
)

from camera_config_utils import normalize_source, save_cameras


class CameraManager(QDialog):
    def __init__(self, parent, config_path: str, cameras: list[dict]):
        super().__init__(parent)
        self.setWindowTitle("摄像头管理")
        self.resize(720, 420)
        self.config_path = config_path

        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "Source"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("新增")
        btn_remove = QPushButton("删除")
        btn_test = QPushButton("测试")
        btn_save = QPushButton("保存")
        btn_add.clicked.connect(self.add_row)
        btn_remove.clicked.connect(self.remove_selected)
        btn_test.clicked.connect(self.test_selected)
        btn_save.clicked.connect(self.save)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_test)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        self.load_cameras(cameras)

    def load_cameras(self, cameras: list[dict]) -> None:
        self.table.setRowCount(0)
        for cam in cameras:
            self.insert_camera(cam)

    def insert_camera(self, cam: dict) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(cam.get("id", ""))))
        self.table.setItem(row, 1, QTableWidgetItem(str(cam.get("name", ""))))
        self.table.setItem(row, 2, QTableWidgetItem(str(cam.get("source", ""))))

    def add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"cam{row + 1:02d}"))
        self.table.setItem(row, 1, QTableWidgetItem(f"Camera-{row + 1:02d}"))
        self.table.setItem(row, 2, QTableWidgetItem("0"))

    def remove_selected(self) -> None:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)

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
        cap.release()
        if ok:
            QMessageBox.information(self, "测试成功", f"摄像头 {source_raw} 可用")
        else:
            QMessageBox.warning(self, "测试失败", f"摄像头 {source_raw} 无法打开")

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
        save_cameras(self.config_path, cameras)
        QMessageBox.information(self, "保存成功", "摄像头配置已保存，重启后生效")
        parent = self.parent()
        if parent and hasattr(parent, "load_cameras_from_manager"):
            parent.load_cameras_from_manager(cameras)
