"""告警事件导出为 CSV 文件。"""
import csv
import logging
from typing import Iterable, Mapping

logger = logging.getLogger(__name__)

EXPORT_FIELDS = [
    "time",
    "ts",
    "camera",
    "level",
    "status",
    "orig_path",
    "annotated_path",
]


def export_alarm_events_csv(path: str, events: Iterable[Mapping]) -> int:
    """将告警事件写入 CSV，返回写入行数。"""
    count = 0
    try:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for ev in events:
                writer.writerow({k: ev.get(k, "") for k in EXPORT_FIELDS})
                count += 1
    except OSError as exc:
        logger.error("导出告警 CSV 失败 %s: %s", path, exc)
        raise
    return count
