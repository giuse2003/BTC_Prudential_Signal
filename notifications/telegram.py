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
from typing import Any

@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


def format_monitor_message(
    signal: str,
    risk_level: str,
    price_eur: float | None,
) -> str:
    """
    Formatta il messaggio operativo condiviso da monitor e comandi Telegram.
    """
    if price_eur is None:
        price_text = "BTC-EUR non disponibile"
    else:
        price_text = f"{int(price_eur):,}".replace(",", ".") + " EUR"

    if signal == "ACQUISTA":
        indication = "Accumulare o acquistare posizioni."
    elif signal == "VENDI":
        indication = "Valutare la riduzione del rischio o vendita."
    else:
        indication = "Attendere. Nessuna nuova operazione consigliata."

    return "\n".join(
        [
            "BTC MONITOR",
            "",
            f"Segnale: {signal}",
            f"Rischio: {risk_level}",
            "",
            "Prezzo:",
            price_text,
            "",
            "Indicazione:",
            indication,
        ]
    )


def send_telegram_message(cfg: TelegramConfig, text: str, timeout_s: int = 20) -> None:
    """
    Invia un messaggio semplice (plain text).
    """
    import requests

    url = f"https://api.telegram.org/bot{cfg.bot_token}/sendMessage"
    payload = {
        "chat_id": cfg.chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    r = requests.post(url, json=payload, timeout=timeout_s)
    r.raise_for_status()


def get_telegram_updates(
    cfg: TelegramConfig,
    offset: int | None = None,
    timeout_s: int = 20,
) -> list[dict[str, Any]]:
    """
    Legge gli aggiornamenti in attesa tramite long polling disabilitato.
    """
    import requests

    url = f"https://api.telegram.org/bot{cfg.bot_token}/getUpdates"
    params: dict[str, int] = {"timeout": 0}
    if offset is not None:
        params["offset"] = offset

    response = requests.get(url, params=params, timeout=timeout_s)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError("Telegram getUpdates non ha restituito ok=true.")
    return list(payload.get("result", []))


def extract_authorized_commands(
    updates: list[dict[str, Any]],
    authorized_chat_id: str,
) -> tuple[list[str], int | None]:
    """
    Estrae i comandi della chat autorizzata e calcola l'offset di conferma.
    """
    commands: list[str] = []
    update_ids: list[int] = []

    for update in updates:
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            update_ids.append(update_id)

        message = update.get("message")
        if not isinstance(message, dict):
            continue

        chat = message.get("chat")
        if not isinstance(chat, dict) or str(chat.get("id")) != str(authorized_chat_id):
            continue

        text = message.get("text")
        if not isinstance(text, str) or not text.strip().startswith("/"):
            continue

        command = text.strip().split(maxsplit=1)[0].split("@", maxsplit=1)[0].lower()
        commands.append(command)

    next_offset = max(update_ids) + 1 if update_ids else None
    return commands, next_offset

