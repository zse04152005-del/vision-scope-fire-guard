import csv
import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)

FIELDNAMES = [
    "ts",
    "time",
    "camera",
    "level",
    "status",
    "orig_path",
    "annotated_path",
]


def write_event(path: str, event: Dict[str, object]) -> None:
    file_exists = os.path.exists(path) and os.path.getsize(path) > 0
    extras = [k for k in event.keys() if k not in FIELDNAMES]
    fieldnames = FIELDNAMES + extras
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            if not file_exists:
                writer.writeheader()
            row = {k: event.get(k, "") for k in fieldnames}
            writer.writerow(row)
    except OSError as exc:
        logger.error("写入事件日志失败 %s: %s", path, exc)
