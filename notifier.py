import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 5.0


def _post_json(url: str, payload: dict) -> None:
    try:
        import requests
    except ImportError:
        logger.warning("requests 未安装，跳过 webhook 通知")
        return
    try:
        resp = requests.post(url, json=payload, timeout=_HTTP_TIMEOUT)
        if resp.status_code >= 400:
            logger.warning("webhook 返回 %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:  # 网络/SSL/超时统一吞掉
        logger.warning("webhook 发送失败 %s: %s", url, exc)


def _fire_and_forget(url: str, payload: dict) -> None:
    t = threading.Thread(target=_post_json, args=(url, payload), daemon=True)
    t.start()


def build_alarm_text(event: dict) -> str:
    return (
        f"[火警告警]\n"
        f"时间: {event.get('time', '')}\n"
        f"摄像头: {event.get('camera', '')}\n"
        f"等级: {event.get('level', '')}"
    )


class AlarmNotifier:
    """封装告警 webhook 通知。配置示例：
    {"dingtalk_url": "https://...", "wecom_url": "https://..."}
    任一字段为空则跳过对应渠道。
    """

    def __init__(self, cfg: Optional[dict] = None):
        cfg = cfg or {}
        self.dingtalk_url = cfg.get("dingtalk_url") or ""
        self.wecom_url = cfg.get("wecom_url") or ""

    def enabled(self) -> bool:
        return bool(self.dingtalk_url or self.wecom_url)

    def notify(self, event: dict) -> None:
        if not self.enabled():
            return
        text = build_alarm_text(event)
        if self.dingtalk_url:
            _fire_and_forget(
                self.dingtalk_url,
                {"msgtype": "text", "text": {"content": text}},
            )
        if self.wecom_url:
            _fire_and_forget(
                self.wecom_url,
                {"msgtype": "text", "text": {"content": text}},
            )
