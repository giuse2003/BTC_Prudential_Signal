"""
Risponde ai comandi Telegram usando l'ultimo stato pubblicato dal monitor.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from live.coingecko import fetch_btc_market
from notifications.telegram import (
    TelegramConfig,
    extract_authorized_commands,
    get_telegram_updates,
    send_telegram_message,
)
from strategy.signals import format_condition_message
from strategy.signals import (
    build_live_signal_frame,
    live_condition_statuses,
    signal_from_condition_statuses,
)


def load_published_status(project_root: Path) -> dict:
    for path in (
        project_root / "docs" / "status.json",
        project_root / "reports" / "status.json",
    ):
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("Nessun status.json pubblicato disponibile.")


def load_published_chart_data(project_root: Path) -> list[dict]:
    for path in (
        project_root / "docs" / "chart-data.json",
        project_root / "reports" / "chart-data.json",
    ):
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return payload
    raise FileNotFoundError("Nessun chart-data.json pubblicato disponibile.")


def _chart_rows_to_daily_frame(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "Date": [row.get("date") for row in rows],
            "Close": [row.get("close") for row in rows],
            "Volume": [row.get("volume") for row in rows],
        }
    )
    frame["Date"] = pd.to_datetime(frame["Date"])
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    frame["Volume"] = pd.to_numeric(frame["Volume"], errors="coerce")
    frame = frame.dropna(subset=["Date", "Close", "Volume"]).sort_values("Date")
    frame["Open"] = frame["Close"]
    frame["High"] = frame["Close"]
    frame["Low"] = frame["Close"]
    return frame.set_index("Date")[["Open", "High", "Low", "Close", "Volume"]]


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


def build_live_signal_message(chart_rows: list[dict]) -> str:
    market = fetch_btc_market(timeout_s=10)
    live_frame = build_live_signal_frame(
        _chart_rows_to_daily_frame(chart_rows),
        live_price_usd=market.price_usd,
        live_volume_24h=market.volume_24h_usd,
        live_time_utc=pd.Timestamp.now(tz="UTC"),
    )
    buy_statuses, sell_statuses = live_condition_statuses(live_frame)
    return format_condition_message(
        signal=signal_from_condition_statuses(buy_statuses, sell_statuses),
        price_eur=market.price_eur,
        buy_statuses=buy_statuses,
        sell_statuses=sell_statuses,
        title="BTC MONITOR LIVE!",
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

    response_sent = False
    project_root = Path(__file__).resolve().parent

    for command in commands:
        if command == "/segnale":
            try:
                message = build_live_signal_message(load_published_chart_data(project_root))
            except Exception:
                message = "Impossibile calcolare il segnale BTC LIVE aggiornato. Riprova tra poco."
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
