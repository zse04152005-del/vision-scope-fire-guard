import logging
import os
from logging.handlers import RotatingFileHandler

_CONFIGURED = False


def setup_logging(output_dir: str, cfg: dict | None = None) -> logging.Logger:
    """初始化全局日志系统（幂等）。写入 <output_dir>/app.log 并同时输出到控制台。"""
    global _CONFIGURED
    cfg = cfg or {}
    level_name = str(cfg.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    max_bytes = int(cfg.get("max_bytes", 1_048_576))
    backup_count = int(cfg.get("backup_count", 3))

    root = logging.getLogger()
    if _CONFIGURED:
        root.setLevel(level)
        return root

    os.makedirs(output_dir, exist_ok=True)
    log_path = os.path.join(output_dir, "app.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)

    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)

    _CONFIGURED = True
    logging.getLogger(__name__).info("日志系统已初始化，输出到 %s", log_path)
    return root
