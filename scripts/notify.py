"""Notification channels — Telegram default. Add Email / Notion / etc. later."""
import os

import httpx


def notify_telegram(message: str) -> None:
    """Send a Markdown-formatted message to a personal Telegram chat.

    4096-char message limit on Telegram — caller should truncate if the
    summary is long.
    """
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    r = httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    r.raise_for_status()
