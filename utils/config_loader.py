import copy
import json
import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "model_path": "best.pt",
    "output_dir": "results",
    "alarm": {
        "hit_threshold": 3,
        "cooldown_seconds": 10,
        "conf_threshold": 0.5,
        "interval_s": 0.2,
    },
    "cameras": [],
    "grid_cols": 3,
    "theme": "dark",
    "logging": {
        "level": "INFO",
        "max_bytes": 1048576,
        "backup_count": 3,
    },
    "perf": {
        "max_fps": 0,
        "infer_size": 0,
        "heartbeat_timeout": 5.0,
    },
    "clip": {
        "pre_seconds": 3,
        "post_seconds": 3,
    },
    "webhook": {
        "dingtalk_url": "",
        "wecom_url": "",
        "email": {
            "smtp_host": "",
            "smtp_port": 587,
            "from": "",
            "password": "",
            "to": [],
        },
    },
}


def _deep_merge(base: dict, overrides: dict) -> dict:
    result = copy.deepcopy(base)
    for k, v in (overrides or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config(path: str) -> dict:
    """加载配置并与默认值深度合并；解析失败返回默认值。"""
    if not os.path.exists(path):
        logger.warning("配置文件不存在，使用默认配置: %s", path)
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("配置文件解析失败 %s: %s，使用默认配置", path, exc)
        return copy.deepcopy(DEFAULT_CONFIG)
    if not isinstance(user_cfg, dict):
        logger.error("配置文件顶层不是对象，使用默认配置: %s", path)
        return copy.deepcopy(DEFAULT_CONFIG)
    return _deep_merge(DEFAULT_CONFIG, user_cfg)
