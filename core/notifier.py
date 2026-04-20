import logging
import smtplib
import threading
from email.mime.text import MIMEText
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
    except Exception as exc:
        logger.warning("webhook 发送失败 %s: %s", url, exc)


def _send_email(cfg: dict, subject: str, body: str) -> None:
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = cfg["from"]
        msg["To"] = ", ".join(cfg["to"])
        host = cfg.get("smtp_host", "smtp.gmail.com")
        port = int(cfg.get("smtp_port", 587))
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(cfg["from"], cfg["password"])
            smtp.sendmail(cfg["from"], cfg["to"], msg.as_string())
    except Exception as exc:
        logger.warning("邮件发送失败: %s", exc)


def _fire_and_forget(target, *args) -> None:
    t = threading.Thread(target=target, args=args, daemon=True)
    t.start()


def build_alarm_text(event: dict) -> str:
    return (
        f"[火警告警]\n"
        f"时间: {event.get('time', '')}\n"
        f"摄像头: {event.get('camera', '')}\n"
        f"等级: {event.get('level', '')}"
    )


class AlarmNotifier:
    """封装告警通知（DingTalk / 企微 Webhook / SMTP 邮件）。

    配置示例：
    {
      "dingtalk_url": "https://...",
      "wecom_url": "https://...",
      "email": {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "from": "user@gmail.com",
        "password": "app_password",
        "to": ["admin@example.com"]
      }
    }
    """

    def __init__(self, cfg: Optional[dict] = None):
        cfg = cfg or {}
        self.dingtalk_url = cfg.get("dingtalk_url") or ""
        self.wecom_url = cfg.get("wecom_url") or ""
        self.email_cfg = cfg.get("email") or {}

    def enabled(self) -> bool:
        return bool(self.dingtalk_url or self.wecom_url or self._email_valid())

    def _email_valid(self) -> bool:
        ec = self.email_cfg
        return bool(ec.get("from") and ec.get("to") and ec.get("password"))

    def notify(self, event: dict) -> None:
        if not self.enabled():
            return
        text = build_alarm_text(event)
        if self.dingtalk_url:
            _fire_and_forget(
                _post_json,
                self.dingtalk_url,
                {"msgtype": "text", "text": {"content": text}},
            )
        if self.wecom_url:
            _fire_and_forget(
                _post_json,
                self.wecom_url,
                {"msgtype": "text", "text": {"content": text}},
            )
        if self._email_valid():
            subject = f"[火警告警] {event.get('camera', '')} - {event.get('time', '')}"
            _fire_and_forget(_send_email, self.email_cfg, subject, text)
