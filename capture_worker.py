import time
from threading import Lock
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage


def next_inference_time(last_ts: float, interval_s: float) -> float:
    return last_ts + interval_s


class CameraWorker(QThread):
    frame_signal = pyqtSignal(str, QImage, float, int, float)
    result_signal = pyqtSignal(str, object, float)
    hit_signal = pyqtSignal(str, bool, float)
    status_signal = pyqtSignal(str, str)
    error_signal = pyqtSignal(str, str)

    def __init__(
        self,
        cam_id: str,
        source: Any,
        model: Any,
        model_lock: Any,
        conf_threshold: float,
        interval_s: float,
        infer_size: int = 0,
        heartbeat_timeout: float = 5.0,
    ):
        super().__init__()
        self.cam_id = cam_id
        self.source = source
        self.model = model
        self.model_lock = model_lock
        self._conf_lock = Lock()
        self._conf_threshold = conf_threshold
        self.interval_s = interval_s
        self.infer_size = int(infer_size) if infer_size else 0
        self.heartbeat_timeout = float(heartbeat_timeout) if heartbeat_timeout else 0.0
        self.running = False
        self.paused = False

    @property
    def conf_threshold(self) -> float:
        with self._conf_lock:
            return self._conf_threshold

    @conf_threshold.setter
    def conf_threshold(self, value: float) -> None:
        with self._conf_lock:
            self._conf_threshold = float(value)

    def set_conf_threshold(self, value: float) -> None:
        self.conf_threshold = value

    def run(self):
        import cv2
        self.running = True
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            self.error_signal.emit(self.cam_id, f"无法打开设备源: {self.source}")
            self.status_signal.emit(self.cam_id, "OFFLINE")
            self.running = False
            return

        last_infer = 0.0
        last_frame_ts = time.time()
        fail_count = 0
        while self.running:
            if self.paused:
                time.sleep(0.1)
                last_frame_ts = time.time()
                continue
            ret, frame = cap.read()
            now_ts = time.time()
            heartbeat_stale = (
                self.heartbeat_timeout > 0
                and now_ts - last_frame_ts > self.heartbeat_timeout
            )
            if (not ret or frame is None or frame.size == 0) or heartbeat_stale:
                fail_count += 1
                if fail_count >= 30 or heartbeat_stale:
                    self.status_signal.emit(self.cam_id, "RECONNECTING")
                    try:
                        cap.release()
                    except Exception:
                        pass
                    time.sleep(1.0)
                    cap = cv2.VideoCapture(self.source)
                    if not cap.isOpened():
                        self.error_signal.emit(self.cam_id, f"重连失败: {self.source}")
                        self.status_signal.emit(self.cam_id, "OFFLINE")
                        time.sleep(1.0)
                    fail_count = 0
                    last_frame_ts = time.time()
                else:
                    time.sleep(0.05)
                continue
            fail_count = 0
            last_frame_ts = now_ts

            now = time.time()
            if now < next_inference_time(last_infer, self.interval_s):
                continue

            last_infer = now
            conf = self.conf_threshold
            infer_frame = frame
            if self.infer_size and self.infer_size > 0:
                h, w = frame.shape[:2]
                long_side = max(h, w)
                if long_side > self.infer_size:
                    scale = self.infer_size / float(long_side)
                    infer_frame = cv2.resize(
                        frame,
                        (int(w * scale), int(h * scale)),
                        interpolation=cv2.INTER_AREA,
                    )
            t0 = time.time()
            with self.model_lock:
                results = self.model(infer_frame, conf=conf)[0]
            inference_time = time.time() - t0

            annotated = results.plot()
            qt_img = self.convert_cv_qt(annotated)
            count = len(results.boxes)
            max_conf = float(results.boxes[0].conf) if count > 0 else 0.0

            self.frame_signal.emit(self.cam_id, qt_img, inference_time, count, max_conf)
            self.result_signal.emit(self.cam_id, results, inference_time)
            hit = count > 0 and max_conf >= conf
            self.hit_signal.emit(self.cam_id, hit, now)
            self.status_signal.emit(self.cam_id, "ONLINE")

        cap.release()
        self.status_signal.emit(self.cam_id, "OFFLINE")

    def stop(self, timeout_ms: int = 3000):
        self.running = False
        if not self.wait(timeout_ms):
            self.terminate()
            self.wait(1000)

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    @staticmethod
    def convert_cv_qt(cv_img):
        import cv2
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        return QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
