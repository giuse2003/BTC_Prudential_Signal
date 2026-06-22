"""
Risponde ai comandi Telegram usando l'ultimo stato pubblicato dal monitor.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from live.coinbase import fetch_spot_price
from notifications.telegram import (
    TelegramConfig,
    extract_authorized_commands,
    get_telegram_updates,
    send_telegram_message,
)
from strategy.signals import format_condition_message


def load_published_status(project_root: Path) -> dict:
    for path in (
        project_root / "docs" / "status.json",
        project_root / "reports" / "status.json",
    ):
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("Nessun status.json pubblicato disponibile.")


def _condition_statuses_from_status(status: dict) -> tuple[list[bool], list[bool]]:
    groups = status.get("condition_groups")
    if not isinstance(groups, dict):
        return [], []

    buy = groups.get("buy")
    sell = groups.get("sell")
    if not isinstance(buy, list) or not isinstance(sell, list):
        return [], []

    return (
        [bool(item.get("passed")) for item in buy if isinstance(item, dict)],
        [bool(item.get("passed")) for item in sell if isinstance(item, dict)],
    )


def build_signal_message(status: dict, price_eur: float | None = None) -> str:
    buy_statuses, sell_statuses = _condition_statuses_from_status(status)
    return format_condition_message(
        signal=str(status.get("signal", "MANTIENI")),
        price_eur=price_eur,
        buy_statuses=buy_statuses,
        sell_statuses=sell_statuses,
        title="BTC MONITOR DAILY!",
    )


def main() -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        raise RuntimeError("Mancano TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID.")

    cfg = TelegramConfig(bot_token=bot_token, chat_id=chat_id)
    updates = get_telegram_updates(cfg)
    commands, next_offset = extract_authorized_commands(updates, chat_id)

    if not updates:
        print("Nessun aggiornamento Telegram in attesa.")
        return

    status = load_published_status(Path(__file__).resolve().parent)
    response_sent = False

    for command in commands:
        if command == "/segnale":
            try:
                price_eur = fetch_spot_price("BTC-EUR", timeout_s=10).price
            except Exception:
                price_eur = status.get("price_eur")

            message = build_signal_message(
                status,
                price_eur=float(price_eur) if price_eur is not None else None,
            )
        elif command in {"/start", "/help"}:
            message = "Comando disponibile:\n/segnale - mostra il segnale BTC corrente"
        else:
            message = "Comando non riconosciuto.\nUsa /segnale"

        send_telegram_message(cfg, message)
        response_sent = True

    if next_offset is not None:
        get_telegram_updates(cfg, offset=next_offset)

    if response_sent:
        print("Risposta al comando Telegram inviata con successo.")
    else:
        print("Nessun comando proveniente dalla chat autorizzata.")


if __name__ == "__main__":
    main()
