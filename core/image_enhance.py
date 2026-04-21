"""低光增强预处理 — CLAHE 自适应直方图均衡，提升暗光场景检测率。"""

import numpy as np


def is_low_light(frame: np.ndarray, threshold: int = 60) -> bool:
    """判断帧是否为低光环境（基于平均亮度）。

    Parameters
    ----------
    frame : BGR numpy array
    threshold : 平均亮度低于此值视为暗光（0-255）
    """
    if frame is None or frame.size == 0:
        return False
    # 快速计算：取绿通道（对人眼亮度贡献最大）的均值
    mean_brightness = frame[:, :, 1].mean()
    return mean_brightness < threshold


def enhance_low_light(frame: np.ndarray, clip_limit: float = 2.0,
                      tile_size: int = 8) -> np.ndarray:
    """对低光帧应用 CLAHE 增强。

    在 LAB 颜色空间的 L 通道上做自适应直方图均衡，
    保留色彩信息的同时提升对比度。

    Parameters
    ----------
    frame : BGR numpy array
    clip_limit : CLAHE 对比度限制
    tile_size : CLAHE 网格大小
    """
    import cv2

    # BGR → LAB
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # 对 L 通道做 CLAHE
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    l_enhanced = clahe.apply(l_channel)

    # 合并并转回 BGR
    lab_enhanced = cv2.merge([l_enhanced, a_channel, b_channel])
    result = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
    return result


def auto_enhance(frame: np.ndarray, brightness_threshold: int = 60,
                 clip_limit: float = 2.0) -> np.ndarray:
    """自动判断并增强：暗光时增强，正常光照时原样返回。"""
    if is_low_light(frame, brightness_threshold):
        return enhance_low_light(frame, clip_limit)
    return frame
