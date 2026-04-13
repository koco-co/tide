"""DingTalk、飞书和 Slack 的 Webhook 通知器。"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from scripts.common import setup_logger

logger = setup_logger(__name__)

MAX_BODY_LENGTH = 4500
_TRUNCATION_SUFFIX = "... (truncated)"


# ---------------------------------------------------------------------------
# 通知载荷
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NotificationPayload:
    title: str
    body: str


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


def _truncate(text: str, max_len: int = MAX_BODY_LENGTH) -> str:
    if len(text) <= max_len:
        return text
    cut = max_len - len(_TRUNCATION_SUFFIX)
    return text[:cut] + _TRUNCATION_SUFFIX


# ---------------------------------------------------------------------------
# 消息格式化函数
# ---------------------------------------------------------------------------


def format_dingtalk(payload: NotificationPayload) -> dict:
    body = _truncate(payload.body)
    text = f"## {payload.title}\n\n{body}"
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": payload.title,
            "text": text,
        },
    }


def format_feishu(payload: NotificationPayload) -> dict:
    body = _truncate(payload.body)
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": payload.title,
                }
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": body,
                }
            ],
        },
    }


def format_slack(payload: NotificationPayload) -> dict:
    body = _truncate(payload.body)
    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": payload.title,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": body,
                },
            },
        ]
    }


# ---------------------------------------------------------------------------
# 格式化器注册表
# ---------------------------------------------------------------------------

FORMATTERS: dict[str, object] = {
    "dingtalk": format_dingtalk,
    "feishu": format_feishu,
    "slack": format_slack,
    "custom": format_dingtalk,
}


# ---------------------------------------------------------------------------
# send_notification
# ---------------------------------------------------------------------------


def send_notification(channel: str, webhook_url: str, payload: NotificationPayload) -> bool:
    formatter = FORMATTERS.get(channel)
    if formatter is None:
        raise ValueError(f"Unknown channel: {channel!r}")

    message = formatter(payload)  # type: ignore[operator]

    try:
        response = httpx.post(webhook_url, json=message, timeout=10)
        return response.status_code == 200
    except Exception:
        logger.exception("Failed to send notification to %s via %s", channel, webhook_url)
        return False
