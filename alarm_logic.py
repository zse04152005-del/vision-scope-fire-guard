from dataclasses import dataclass
from typing import Dict


@dataclass
class AlarmState:
    hits: int = 0
    last_alert_ts: float = 0.0


class AlarmTracker:
    def __init__(self, hit_threshold: int, cooldown_seconds: int):
        self.hit_threshold = hit_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state: Dict[str, AlarmState] = {}

    def update(self, cam_id: str, hit: bool, ts: float):
        st = self.state.setdefault(cam_id, AlarmState())
        st.hits = st.hits + 1 if hit else 0
        if st.hits >= self.hit_threshold:
            if ts - st.last_alert_ts >= self.cooldown_seconds:
                st.last_alert_ts = ts
                return {"camera": cam_id, "level": "confirm", "ts": ts}
        return None
