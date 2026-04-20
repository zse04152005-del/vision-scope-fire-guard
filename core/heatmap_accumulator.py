"""告警热力图累积器 — 追踪每帧检测区域，生成频率热力图覆盖层。"""

import numpy as np
from typing import Dict, Optional


class HeatmapAccumulator:
    """维护每台摄像头的低分辨率热力密度图。

    Parameters
    ----------
    map_w, map_h : int
        内部热力图分辨率（低分辨率，减少计算量）。
    decay : float
        每帧衰减系数（<1），使旧热点逐渐消退。
    """

    def __init__(self, map_w: int = 80, map_h: int = 60, decay: float = 0.997):
        self.map_w = map_w
        self.map_h = map_h
        self.decay = decay
        self._maps: Dict[str, np.ndarray] = {}

    def update(self, cam_id: str, boxes, frame_w: int, frame_h: int) -> None:
        """将当前帧的检测框区域累加到热力图上。"""
        hmap = self._maps.get(cam_id)
        if hmap is None:
            hmap = np.zeros((self.map_h, self.map_w), dtype=np.float32)
            self._maps[cam_id] = hmap

        # 衰减
        hmap *= self.decay

        if frame_w <= 0 or frame_h <= 0:
            return

        # 累加检测区域
        scale_x = self.map_w / frame_w
        scale_y = self.map_h / frame_h

        for box in boxes:
            try:
                coords = box.xyxy[0]
                if hasattr(coords, 'cpu'):
                    coords = coords.cpu().numpy()
                x1 = max(0, int(float(coords[0]) * scale_x))
                y1 = max(0, int(float(coords[1]) * scale_y))
                x2 = min(self.map_w, int(float(coords[2]) * scale_x))
                y2 = min(self.map_h, int(float(coords[3]) * scale_y))
                if x2 > x1 and y2 > y1:
                    hmap[y1:y2, x1:x2] += 1.0
            except (AttributeError, TypeError, IndexError):
                pass

    def get_overlay(self, cam_id: str, target_w: int, target_h: int) -> Optional[np.ndarray]:
        """生成彩色热力图覆盖层（BGR），尺寸为 target_w x target_h。

        Returns None if no data.
        """
        hmap = self._maps.get(cam_id)
        if hmap is None or hmap.max() <= 0:
            return None

        import cv2

        # 归一化到 0-255
        normalized = (hmap / hmap.max() * 255).astype(np.uint8)
        # 应用颜色映射
        colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
        # 缩放到目标尺寸
        overlay = cv2.resize(colored, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
        return overlay

    def get_density(self, cam_id: str) -> Optional[np.ndarray]:
        """返回原始密度图（float32），供外部分析。"""
        return self._maps.get(cam_id)

    def reset(self, cam_id: str) -> None:
        """重置指定摄像头的热力图。"""
        if cam_id in self._maps:
            self._maps[cam_id] = np.zeros((self.map_h, self.map_w), dtype=np.float32)
