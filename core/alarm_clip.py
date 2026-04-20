"""告警录像片段保存工具 — 将 ring buffer 中的帧列表写入 .avi 视频文件。"""

import logging
import threading

logger = logging.getLogger(__name__)


def save_clip(output_path: str, frames: list, fps: float = 5.0):
    """将 BGR numpy 帧列表写入视频文件，返回实际路径或 None。"""
    if not frames:
        return None
    try:
        import cv2

        if not output_path.lower().endswith(".avi"):
            output_path = output_path.rsplit(".", 1)[0] + ".avi"
        h, w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        if not writer.isOpened():
            logger.warning("VideoWriter 打开失败: %s", output_path)
            return None
        for frame in frames:
            writer.write(frame)
        writer.release()
        logger.info("告警录像已保存: %s (%d 帧)", output_path, len(frames))
        return output_path
    except Exception as exc:
        logger.exception("保存告警录像失败: %s", exc)
        return None


def save_clip_async(output_path: str, frames: list, fps: float = 5.0, callback=None):
    """后台线程保存录像片段。callback(path_or_none) 在完成时调用。"""

    def _worker():
        path = save_clip(output_path, frames, fps)
        if callback:
            callback(path)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
