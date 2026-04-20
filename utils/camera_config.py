import json
import os
import re
from typing import List, Dict, Any

_ENV_RE = re.compile(r"\$\{(\w+)\}")


def _expand_env(value: str) -> str:
    """将 ${VAR_NAME} 占位符替换为环境变量值。"""
    def _replace(m):
        name = m.group(1)
        return os.environ.get(name, m.group(0))
    return _ENV_RE.sub(_replace, value)


def normalize_source(value: Any):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed.isdigit():
            return int(trimmed)
        return _expand_env(trimmed)
    return value


def save_cameras(config_path: str, cameras: List[Dict[str, Any]]) -> None:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    data["cameras"] = cameras
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
