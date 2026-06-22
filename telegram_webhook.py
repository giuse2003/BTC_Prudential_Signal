"""
Webhook Telegram FastAPI per risposte quasi in tempo reale.

Il servizio non calcola segnali e non conserva stato locale: per ogni comando
scarica l'ultimo docs/status.json pubblicato su GitHub.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import requests
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from notifications.telegram import (
    TelegramConfig,
    send_telegram_message,
)
from strategy.signals import format_condition_message
from telegram_subscribers import SupabaseSubscriberStore, TelegramSubscriber


STATUS_JSON_URL = (
    "https://raw.githubusercontent.com/"
    "giuse2003/BTC_Prudential_Signal/main/docs/status.json"
)
STATUS_ERROR_MESSAGE = (
    "Impossibile recuperare il segnale BTC aggiornato. Riprova tra poco."
)
HELP_MESSAGE = "\n".join(
    [
        "BTC PRUDENTIAL SIGNAL",
        "",
        "/segnale - mostra il segnale BTC corrente",
        "/iscrivimi - ricevi notifiche quando cambia segnale o rischio",
        "/disiscrivimi - interrompi le notifiche automatiche",
        "/privacy - informazioni sui dati memorizzati",
    ]
)
PRIVACY_MESSAGE = "\n".join(
    [
        "PRIVACY",
        "",
        "Per gestire le notifiche vengono memorizzati il tuo identificativo "
        "Telegram, il nome pubblico e lo stato dell'iscrizione.",
        "Il numero di cellulare non viene richiesto o memorizzato.",
        "Puoi revocare il consenso in qualsiasi momento con /disiscrivimi.",
    ]
)
SUBSCRIBED_MESSAGE = "\n".join(
    [
        "Iscrizione attiva.",
        "",
        "Riceverai un messaggio soltanto quando cambia il segnale BTC o il "
        "livello di rischio.",
        "Puoi annullare l'iscrizione con /disiscrivimi.",
    ]
)
UNSUBSCRIBED_MESSAGE = "Iscrizione disattivata. Non riceverai nuovi segnali."
NOT_SUBSCRIBED_MESSAGE = "Non risulta alcuna iscrizione da disattivare."
SUBSCRIPTION_ERROR_MESSAGE = (
    "Non riesco ad aggiornare l'iscrizione in questo momento. Riprova tra poco."
)

logger = logging.getLogger(__name__)
app = FastAPI(title="BTC Prudential Signal Telegram Webhook")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://giuse2003.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_methods=["GET"],
    allow_headers=["Accept"],
)


@dataclass(frozen=True)
class TelegramCommand:
    command: str
    chat_id: int
    user_id: int | None
    username: str | None
    first_name: str | None
    language_code: str | None


def extract_command(update: dict[str, Any]) -> TelegramCommand | None:
    """Estrae un comando ricevuto in una chat privata Telegram."""
    message = update.get("message")
    if not isinstance(message, dict):
        return None

    chat = message.get("chat")
    if not isinstance(chat, dict) or chat.get("type") not in {None, "private"}:
        return None

    chat_id = chat.get("id")
    if not isinstance(chat_id, int):
        return None

    text = message.get("text")
    if not isinstance(text, str) or not text.strip().startswith("/"):
        return None

    sender = message.get("from")
    if not isinstance(sender, dict):
        sender = {}

    user_id = sender.get("id")
    parts = text.strip().split(maxsplit=1)
    command = parts[0].split("@", maxsplit=1)[0].lower()
    if command == "/start" and len(parts) > 1 and parts[1].strip() == "iscrivimi":
        command = "/iscrivimi"

    return TelegramCommand(
        command=command,
        chat_id=chat_id,
        user_id=user_id if isinstance(user_id, int) else None,
        username=_optional_text(sender.get("username")),
        first_name=_optional_text(sender.get("first_name")),
        language_code=_optional_text(sender.get("language_code")),
    )


def _optional_text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


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
    Converte docs/status.json nel formato compatto Telegram DAILY.
    """
    price_eur = status.get("price_eur")
    condition_groups = status.get("condition_groups")
    buy_conditions = condition_groups.get("buy", []) if isinstance(condition_groups, dict) else []
    sell_conditions = condition_groups.get("sell", []) if isinstance(condition_groups, dict) else []
    buy_statuses = [
        bool(condition.get("passed"))
        for condition in buy_conditions
        if isinstance(condition, dict)
    ]
    sell_statuses = [
        bool(condition.get("passed"))
        for condition in sell_conditions
        if isinstance(condition, dict)
    ]

    return format_condition_message(
        signal=str(status.get("signal", "MANTIENI")),
        price_eur=float(price_eur) if price_eur is not None else None,
        buy_statuses=buy_statuses,
        sell_statuses=sell_statuses,
        title="BTC MONITOR DAILY!",
    )


def process_command(
    request: TelegramCommand,
    cfg: TelegramConfig,
    subscriber_store: SupabaseSubscriberStore | None,
) -> None:
    """
    Elabora il comando dopo che il webhook ha gia restituito HTTP 200.
    """
    if request.command == "/segnale":
        try:
            message = build_signal_message(fetch_github_status())
        except Exception:
            logger.exception("Impossibile recuperare docs/status.json da GitHub.")
            message = STATUS_ERROR_MESSAGE
    elif request.command in {"/start", "/help"}:
        message = HELP_MESSAGE
    elif request.command == "/privacy":
        message = PRIVACY_MESSAGE
    elif request.command == "/iscrivimi":
        if subscriber_store is None:
            message = SUBSCRIPTION_ERROR_MESSAGE
        else:
            try:
                subscriber_store.subscribe(
                    TelegramSubscriber(
                        telegram_chat_id=request.chat_id,
                        telegram_user_id=request.user_id,
                        telegram_username=request.username,
                        telegram_first_name=request.first_name,
                        telegram_language_code=request.language_code,
                    )
                )
                message = SUBSCRIBED_MESSAGE
            except Exception:
                logger.exception("Registrazione dell'iscrizione non riuscita.")
                message = SUBSCRIPTION_ERROR_MESSAGE
    elif request.command == "/disiscrivimi":
        if subscriber_store is None:
            message = SUBSCRIPTION_ERROR_MESSAGE
        else:
            try:
                removed = subscriber_store.unsubscribe(request.chat_id)
                message = UNSUBSCRIBED_MESSAGE if removed else NOT_SUBSCRIBED_MESSAGE
            except Exception:
                logger.exception("Disattivazione dell'iscrizione non riuscita.")
                message = SUBSCRIPTION_ERROR_MESSAGE
    else:
        message = "Comando non riconosciuto.\nUsa /help"

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


@app.get("/subscribers/count")
def subscriber_count() -> dict[str, int]:
    """Restituisce soltanto il numero aggregato degli iscritti attivi."""
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not supabase_url or not supabase_key:
        raise HTTPException(status_code=503, detail="Servizio iscritti non configurato.")

    try:
        active_subscribers = SupabaseSubscriberStore(
            supabase_url,
            supabase_key,
        ).count_active()
    except Exception as exc:
        logger.exception("Conteggio degli iscritti Supabase non riuscito.")
        raise HTTPException(
            status_code=502,
            detail="Conteggio iscritti temporaneamente non disponibile.",
        ) from exc

    return {"active_subscribers": active_subscribers}


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
    webhook_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "").strip()
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not bot_token:
        raise HTTPException(status_code=503, detail="Configurazione Telegram mancante.")

    if webhook_secret and x_telegram_bot_api_secret_token != webhook_secret:
        raise HTTPException(status_code=403, detail="Webhook secret non valido.")

    command = extract_command(update)
    if command is not None:
        cfg = TelegramConfig(bot_token=bot_token, chat_id=str(command.chat_id))
        subscriber_store = (
            SupabaseSubscriberStore(supabase_url, supabase_key)
            if supabase_url and supabase_key
            else None
        )
        background_tasks.add_task(process_command, command, cfg, subscriber_store)

    return {"ok": True}
