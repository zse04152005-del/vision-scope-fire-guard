import logging
import os
import time
from typing import Tuple

logger = logging.getLogger(__name__)


def build_alarm_paths(output_dir: str, cam_id: str, ts: float) -> Tuple[str, str]:
    ts_str = time.strftime("%Y%m%d_%H%M%S", time.gmtime(ts))
    base = f"{cam_id}_{ts_str}"
    orig_path = os.path.join(output_dir, f"{base}_orig.jpg")
    ann_path = os.path.join(output_dir, f"{base}_annotated.jpg")
    return orig_path, ann_path


def _imwrite_unicode(path: str, img) -> bool:
    """兼容中文路径的图片写入：走 imencode + 二进制写文件。"""
    try:
        import cv2
    except Exception as exc:
        raise RuntimeError("OpenCV is required to save alarm images.") from exc
    ext = os.path.splitext(path)[1] or ".jpg"
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        logger.error("cv2.imencode 失败: %s", path)
        return False
    try:
        with open(path, "wb") as f:
            f.write(buf.tobytes())
        return True
    except OSError as exc:
        logger.error("写入告警图片失败 %s: %s", path, exc)
        return False


def save_alarm_images(output_dir: str, cam_id: str, ts: float, orig_img, annotated_img) -> Tuple[str, str]:
    orig_path, ann_path = build_alarm_paths(output_dir, cam_id, ts)
    os.makedirs(output_dir, exist_ok=True)
    ok1 = _imwrite_unicode(orig_path, orig_img)
    ok2 = _imwrite_unicode(ann_path, annotated_img)
    return (orig_path if ok1 else None, ann_path if ok2 else None)
