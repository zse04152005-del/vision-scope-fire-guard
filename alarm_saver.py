import os
import time
from typing import Tuple


def build_alarm_paths(output_dir: str, cam_id: str, ts: float) -> Tuple[str, str]:
    ts_str = time.strftime("%Y%m%d_%H%M%S", time.gmtime(ts))
    base = f"{cam_id}_{ts_str}"
    orig_path = os.path.join(output_dir, f"{base}_orig.jpg")
    ann_path = os.path.join(output_dir, f"{base}_annotated.jpg")
    return orig_path, ann_path


def save_alarm_images(output_dir: str, cam_id: str, ts: float, orig_img, annotated_img) -> Tuple[str, str]:
    orig_path, ann_path = build_alarm_paths(output_dir, cam_id, ts)
    os.makedirs(output_dir, exist_ok=True)
    try:
        import cv2
    except Exception as exc:
        raise RuntimeError("OpenCV is required to save alarm images.") from exc
    cv2.imwrite(orig_path, orig_img)
    cv2.imwrite(ann_path, annotated_img)
    return orig_path, ann_path
