"""
Webhook Telegram FastAPI per risposte quasi in tempo reale.

Il servizio non calcola segnali e non conserva stato locale: per ogni comando
scarica l'ultimo docs/status.json pubblicato su GitHub.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException

from notifications.telegram import (
    TelegramConfig,
    format_monitor_message,
    send_telegram_message,
)


STATUS_JSON_URL = (
    "https://raw.githubusercontent.com/"
    "giuse2003/BTC_Prudential_Signal/main/docs/status.json"
)
STATUS_ERROR_MESSAGE = (
    "Impossibile recuperare il segnale BTC aggiornato. Riprova tra poco."
)
HELP_MESSAGE = "Comando disponibile:\n/segnale - mostra il segnale BTC corrente"

logger = logging.getLogger(__name__)
app = FastAPI(title="BTC Prudential Signal Telegram Webhook")


def extract_command(update: dict[str, Any], authorized_chat_id: str) -> str | None:
    """
    Estrae un comando solo dalla chat Telegram autorizzata.
    """
    message = update.get("message")
    if not isinstance(message, dict):
        return None

    chat = message.get("chat")
    if not isinstance(chat, dict) or str(chat.get("id")) != str(authorized_chat_id):
        return None

    text = message.get("text")
    if not isinstance(text, str) or not text.strip().startswith("/"):
        return None

    return text.strip().split(maxsplit=1)[0].split("@", maxsplit=1)[0].lower()


def fetch_github_status(timeout_s: int = 8) -> dict[str, Any]:
    """
    Scarica sempre lo stato corrente dal file Raw pubblico su GitHub.
    """
    response = requests.get(
        STATUS_JSON_URL,
        headers={
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        },
        timeout=timeout_s,
    )
    response.raise_for_status()
    status = response.json()
    if not isinstance(status, dict):
        raise ValueError("Il file status.json non contiene un oggetto JSON.")
    return status


def build_signal_message(status: dict[str, Any]) -> str:
    """
    Converte docs/status.json nel formato Telegram gia usato dal progetto.
    """
    price_eur = status.get("price_eur")
    return format_monitor_message(
        signal=str(status.get("signal", "MANTIENI")),
        risk_level=str(status.get("risk_level", "MEDIO")),
        price_eur=float(price_eur) if price_eur is not None else None,
    )


def process_command(command: str, cfg: TelegramConfig) -> None:
    """
    Elabora il comando dopo che il webhook ha gia restituito HTTP 200.
    """
    if command == "/segnale":
        try:
            message = build_signal_message(fetch_github_status())
        except Exception:
            logger.exception("Impossibile recuperare docs/status.json da GitHub.")
            message = STATUS_ERROR_MESSAGE
    elif command in {"/start", "/help"}:
        message = HELP_MESSAGE
    else:
        message = "Comando non riconosciuto.\nUsa /segnale"

    try:
        send_telegram_message(cfg, message)
    except Exception:
        logger.exception("Invio della risposta Telegram non riuscito.")


@app.get("/")
def health_check() -> dict[str, str]:
    """
    Endpoint di controllo per Render.
    """
    return {"status": "ok"}


@app.post("/webhook")
def telegram_webhook(
    update: dict[str, Any],
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    """
    Riceve gli update Telegram e accoda rapidamente la risposta.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    webhook_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()

    if not bot_token or not chat_id:
        raise HTTPException(status_code=503, detail="Configurazione Telegram mancante.")

    if webhook_secret and x_telegram_bot_api_secret_token != webhook_secret:
        raise HTTPException(status_code=403, detail="Webhook secret non valido.")

    command = extract_command(update, chat_id)
    if command is not None:
        cfg = TelegramConfig(bot_token=bot_token, chat_id=chat_id)
        background_tasks.add_task(process_command, command, cfg)

    return {"ok": True}
