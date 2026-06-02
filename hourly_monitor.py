"""
Job "hourly" pensato per GitHub Actions (piano gratuito).

Comportamento:
- Scarica/aggiorna dati giornalieri BTC-USD (Yahoo Finance) e calcola indicatori giornalieri.
- Calcola segnale "di regime" (prudente).
- Legge prezzo spot "live" da Coinbase in EUR.
- Invia notifica Telegram SOLO se cambia il segnale rispetto al run precedente.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from data.fetch_yahoo import fetch_btc_daily_csv, load_daily_csv
from indicators.technical_indicators import compute_all_indicators
from live.coinbase import fetch_spot_price
from notifications.telegram import TelegramConfig, send_telegram_message
from strategy.signals import compute_signals, explain_latest_row
from state.state_store import MonitorState, load_state, save_state


def main() -> None:
    # Telegram secrets (GitHub Actions -> Settings -> Secrets and variables -> Actions)
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        raise RuntimeError("Mancano TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID nelle variabili d'ambiente.")

    # Coppia spot live (Coinbase). Default: BTC-EUR per visualizzazione
    live_pair = os.environ.get("LIVE_PAIR", "BTC-EUR").strip()

    project_root = Path(__file__).resolve().parent
    state_path = project_root / ".state" / "state.json"

    # 1) Stato precedente
    state = load_state(state_path)

    # 2) Dati giornalieri + indicatori (sempre su BTC-USD per lo storico)
    csv_path = fetch_btc_daily_csv(symbol="BTC-USD", force_download=True)
    df = load_daily_csv(csv_path)
    df_ind = compute_all_indicators(df)
    df_sig = compute_signals(df_ind)

    latest = df_sig.iloc[-1]
    signal = str(latest["Segnale"])

    # 3) Prezzo spot live (in EUR)
    spot_eur = fetch_spot_price(pair=live_pair).price

    # 4) Eventi: notifica solo se cambia il segnale o se prima eravamo a None
    signal_changed = (state.last_signal is None) or (signal != state.last_signal)

    must_notify = signal_changed

    # 5) Invio Telegram (solo se serve)
    if must_notify:
        cfg = TelegramConfig(bot_token=bot_token, chat_id=chat_id)
        msg = explain_latest_row(df_sig, price_eur=spot_eur)
        send_telegram_message(cfg, msg)

    # 6) Salvataggio stato
    state.last_signal = signal
    state.last_spot_price = float(spot_eur)
    save_state(state_path, state)


if __name__ == "__main__":
    main()
