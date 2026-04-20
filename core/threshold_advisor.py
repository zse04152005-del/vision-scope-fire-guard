"""智能置信度自适应顾问 — 根据告警历史数据为每个摄像头生成阈值调整建议。"""

from typing import List, Dict


# 频率阈值
_HIGH_FREQ_HOURLY = 15   # >15/h 极可能误报过多
_MED_FREQ_HOURLY = 8     # >8/h  偏高
_NEAR_EDGE_RATIO = 0.60  # 60%+ 告警置信度紧贴阈值边缘 → 建议上调


class ThresholdAdvisor:
    """分析告警历史，输出每台摄像头的置信度阈值建议。"""

    def __init__(self, current_threshold: float):
        self.threshold = current_threshold

    def analyze(self, alarm_events: list, cameras: list) -> List[Dict]:
        cam_ids = [c.get("id", "") for c in cameras]
        grouped: Dict[str, list] = {cid: [] for cid in cam_ids}
        for ev in alarm_events:
            cam = ev.get("camera", "")
            if cam in grouped:
                grouped[cam].append(ev)

        return [self._analyze_camera(cid, grouped[cid]) for cid in cam_ids]

    def _analyze_camera(self, cam_id: str, events: list) -> dict:
        result = {
            "camera": cam_id,
            "alarm_count": len(events),
            "suggestion": "keep",      # keep / raise / lower
            "recommended": self.threshold,
            "reason": "",
        }

        if not events:
            result["reason"] = "无告警记录，当前阈值适中"
            return result

        # ── 频率分析 ──
        timestamps = sorted(ev.get("ts", 0) for ev in events)
        span_h = max(0.1, (timestamps[-1] - timestamps[0]) / 3600) if len(timestamps) > 1 else 1.0
        hourly = len(events) / span_h

        if hourly > _HIGH_FREQ_HOURLY:
            result.update(
                suggestion="raise",
                recommended=min(0.95, self.threshold + 0.10),
                reason=f"告警频率极高 ({hourly:.1f}/h)，疑似误报较多，建议上调",
            )
            return result

        if hourly > _MED_FREQ_HOURLY:
            result.update(
                suggestion="raise",
                recommended=min(0.90, self.threshold + 0.05),
                reason=f"告警频率偏高 ({hourly:.1f}/h)，建议小幅上调",
            )
            return result

        # ── 置信度分布分析 ──
        confs = [ev["max_conf"] for ev in events if "max_conf" in ev]
        if confs:
            near_edge = sum(1 for c in confs if c < self.threshold + 0.10)
            ratio = near_edge / len(confs)
            if ratio > _NEAR_EDGE_RATIO and len(confs) >= 3:
                result.update(
                    suggestion="raise",
                    recommended=min(0.90, self.threshold + 0.05),
                    reason=f"{ratio * 100:.0f}% 告警贴近阈值边缘，建议上调以过滤边缘误报",
                )
                return result

            avg = sum(confs) / len(confs)
            if avg > 0.85 and hourly < 3:
                result.update(
                    suggestion="lower",
                    recommended=max(0.30, self.threshold - 0.05),
                    reason=f"告警均为高置信度 (avg {avg:.0%})，频率低，可适当下调提升灵敏度",
                )
                return result

        result["reason"] = f"告警频率正常 ({hourly:.1f}/h)，阈值适中"
        return result
