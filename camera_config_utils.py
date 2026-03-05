import json
from typing import List, Dict, Any


def normalize_source(value: Any):
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed.isdigit():
            return int(trimmed)
        return trimmed
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
