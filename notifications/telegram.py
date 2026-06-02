"""
Invio messaggi Telegram via Bot API.

Richiede:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

Consiglio:
- usa Secrets su GitHub Actions, non hardcodare mai credenziali nel repo.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


def send_telegram_message(cfg: TelegramConfig, text: str, timeout_s: int = 20) -> None:
    """
    Invia un messaggio semplice (plain text).
    """
    url = f"https://api.telegram.org/bot{cfg.bot_token}/sendMessage"
    payload = {
        "chat_id": cfg.chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=timeout_s)
    r.raise_for_status()

