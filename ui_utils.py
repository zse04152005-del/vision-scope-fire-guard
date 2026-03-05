from typing import List, Dict


def reorder_camera_order(order: List[str], source_id: str, target_id: str) -> List[str]:
    if source_id == target_id:
        return list(order)
    if source_id not in order or target_id not in order:
        return list(order)
    new_order = list(order)
    i = new_order.index(source_id)
    j = new_order.index(target_id)
    new_order[i], new_order[j] = new_order[j], new_order[i]
    return new_order


def filter_alarm_events(events: List[Dict[str, str]], text: str, level: str) -> List[Dict[str, str]]:
    text = (text or "").strip().lower()
    level = (level or "all").lower()
    filtered = []
    for ev in events:
        if level != "all" and ev.get("level", "").lower() != level:
            continue
        if text:
            hay = f"{ev.get('camera', '')} {ev.get('time', '')} {ev.get('level', '')}".lower()
            if text not in hay:
                continue
        filtered.append(ev)
    return filtered
