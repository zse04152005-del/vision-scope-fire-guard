"""火焰蔓延趋势分析 — 追踪 bbox 面积变化，判定火势是否在扩大。"""

from collections import deque
from typing import Dict, List, Tuple


# 趋势等级
TREND_STABLE = "stable"        # 面积稳定或无检测
TREND_GROWING = "growing"      # 面积缓慢增长
TREND_SPREADING = "spreading"  # 面积快速增长（蔓延）


class SpreadAnalyzer:
    """追踪每台摄像头的火焰面积变化趋势。

    Parameters
    ----------
    window_size : int
        保留的历史帧数量。
    spread_ratio : float
        最近 1/3 窗口平均面积 / 最早 1/3 窗口平均面积 > 此值 → spreading。
    grow_ratio : float
        同上但阈值较低 → growing。
    """

    def __init__(self, window_size: int = 20, spread_ratio: float = 2.0, grow_ratio: float = 1.3):
        self.window_size = max(6, window_size)
        self.spread_ratio = spread_ratio
        self.grow_ratio = grow_ratio
        self._history: Dict[str, deque] = {}

    def update(self, cam_id: str, boxes, frame_w: int, frame_h: int, ts: float) -> str:
        """输入当前帧检测框，返回趋势等级。

        Parameters
        ----------
        boxes : ultralytics boxes or list of (x1, y1, x2, y2)
        frame_w, frame_h : 帧宽高，用于归一化面积
        ts : 当前时间戳
        """
        total_area = self._compute_total_area(boxes, frame_w, frame_h)
        history = self._history.setdefault(cam_id, deque(maxlen=self.window_size))
        history.append((ts, total_area))
        return self._analyze(history)

    def get_trend(self, cam_id: str) -> str:
        """获取指定摄像头当前趋势。"""
        history = self._history.get(cam_id)
        if not history:
            return TREND_STABLE
        return self._analyze(history)

    def get_chart_data(self, cam_id: str) -> List[Tuple[float, float]]:
        """返回 (相对时间秒, 归一化面积) 列表供绘图使用。"""
        history = self._history.get(cam_id)
        if not history or len(history) < 2:
            return []
        t0 = history[0][0]
        return [(t - t0, area) for t, area in history]

    def _analyze(self, history: deque) -> str:
        if len(history) < 6:
            return TREND_STABLE

        n = len(history)
        third = n // 3

        # 早期 1/3 与 最近 1/3 的平均面积比较
        early = [area for _, area in list(history)[:third]]
        recent = [area for _, area in list(history)[-third:]]

        avg_early = sum(early) / len(early) if early else 0
        avg_recent = sum(recent) / len(recent) if recent else 0

        if avg_early <= 0:
            # 从无到有也算 growing
            return TREND_GROWING if avg_recent > 0 else TREND_STABLE

        ratio = avg_recent / avg_early
        if ratio >= self.spread_ratio:
            return TREND_SPREADING
        elif ratio >= self.grow_ratio:
            return TREND_GROWING
        return TREND_STABLE

    @staticmethod
    def _compute_total_area(boxes, frame_w: int, frame_h: int) -> float:
        """计算所有 bbox 面积占帧面积的比例（0~1）。"""
        frame_area = frame_w * frame_h
        if frame_area <= 0:
            return 0.0
        total = 0.0
        for box in boxes:
            try:
                # ultralytics Boxes object: box.xyxy is tensor
                coords = box.xyxy[0]
                if hasattr(coords, 'cpu'):
                    coords = coords.cpu().numpy()
                w = float(coords[2] - coords[0])
                h = float(coords[3] - coords[1])
                total += w * h
            except (AttributeError, TypeError, IndexError):
                pass
        return total / frame_area
