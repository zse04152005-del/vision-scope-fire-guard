"""ROI (Region of Interest) 管理器 — 每摄像头可配置多边形关注区域，仅区域内检测触发告警。"""

import json
import logging
import os
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ROIManager:
    """管理每个摄像头的多边形 ROI 区域。

    ROI 以归一化坐标 (0~1) 存储，适配任意分辨率。
    """

    def __init__(self, config_path: str = ""):
        self._rois: dict[str, list[list[tuple[float, float]]]] = {}
        self._config_path = config_path
        if config_path and os.path.exists(config_path):
            self.load(config_path)

    def set_roi(self, cam_id: str, polygons: list[list[tuple[float, float]]]) -> None:
        """设置摄像头的 ROI 多边形列表（归一化坐标）。"""
        self._rois[cam_id] = polygons

    def get_roi(self, cam_id: str) -> list[list[tuple[float, float]]]:
        """获取摄像头的 ROI 多边形列表。"""
        return self._rois.get(cam_id, [])

    def clear_roi(self, cam_id: str) -> None:
        """清除摄像头的 ROI。"""
        self._rois.pop(cam_id, None)

    def has_roi(self, cam_id: str) -> bool:
        return bool(self._rois.get(cam_id))

    def filter_boxes(self, cam_id: str, boxes, img_w: int, img_h: int) -> list[int]:
        """返回落在 ROI 内的 box 索引列表。

        如果该摄像头没有设置 ROI，返回全部索引（不过滤）。
        判断标准：bbox 中心点是否在任一 ROI 多边形内。

        Parameters
        ----------
        cam_id : 摄像头 ID
        boxes : ultralytics Results.boxes 对象
        img_w, img_h : 图像宽高（用于反归一化）

        Returns
        -------
        在 ROI 内的 box 索引列表
        """
        polygons = self._rois.get(cam_id, [])
        if not polygons:
            return list(range(len(boxes)))

        # 将归一化多边形转为像素坐标
        pixel_polygons = []
        for poly in polygons:
            pts = np.array(
                [(int(x * img_w), int(y * img_h)) for x, y in poly],
                dtype=np.int32,
            )
            pixel_polygons.append(pts)

        kept = []
        for i, box in enumerate(boxes):
            try:
                coords = box.xyxy[0]
                if hasattr(coords, 'cpu'):
                    coords = coords.cpu().numpy()
                x1, y1, x2, y2 = coords[:4]
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
            except Exception:
                kept.append(i)
                continue

            for pts in pixel_polygons:
                if cv2.pointPolygonTest(pts, (float(cx), float(cy)), False) >= 0:
                    kept.append(i)
                    break

        return kept

    def draw_overlay(self, frame: np.ndarray, cam_id: str,
                     color: tuple = (0, 255, 0), alpha: float = 0.15) -> np.ndarray:
        """在帧上绘制 ROI 半透明覆盖层。"""
        polygons = self._rois.get(cam_id, [])
        if not polygons:
            return frame

        h, w = frame.shape[:2]
        overlay = frame.copy()
        for poly in polygons:
            pts = np.array(
                [(int(x * w), int(y * h)) for x, y in poly],
                dtype=np.int32,
            )
            cv2.fillPoly(overlay, [pts], color)
            cv2.polylines(frame, [pts], True, color, 2)

        return cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0)

    def save(self, path: str = "") -> None:
        """保存 ROI 配置到 JSON 文件。"""
        path = path or self._config_path
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._rois, f, ensure_ascii=False, indent=2)
            logger.info("ROI 配置已保存: %s", path)
        except Exception as exc:
            logger.error("保存 ROI 配置失败: %s", exc)

    def load(self, path: str = "") -> None:
        """从 JSON 文件加载 ROI 配置。"""
        path = path or self._config_path
        if not path or not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._rois = data
                logger.info("已加载 ROI 配置: %d 个摄像头", len(self._rois))
        except Exception as exc:
            logger.error("加载 ROI 配置失败: %s", exc)
