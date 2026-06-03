"""
Job "hourly" pensato per GitHub Actions (piano gratuito).

Comportamento:
- Scarica/aggiorna dati giornalieri BTC-USD (Yahoo Finance) e calcola indicatori giornalieri.
- Calcola segnale "di regime" (prudente).
- Legge prezzo spot "live" da Coinbase in EUR.
- Invia notifica Telegram se cambia il segnale notificato o se il rischio diventa ALTO.
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
from reports.generate import save_status_json


def main() -> None:
    # Telegram secrets
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        raise RuntimeError("Mancano TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID nelle variabili d'ambiente.")

    project_root = Path(__file__).resolve().parent
    state_path = project_root / ".state" / "state.json"

    # 1) Stato precedente
    state = load_state(state_path)

    # 2) Dati giornalieri + indicatori (con doppia valuta USD/EUR)
    csv_path_usd = fetch_btc_daily_csv(symbol="BTC-USD", force_download=True, is_optional=False)
    df_usd = load_daily_csv(csv_path_usd)
    
    csv_path_eur = fetch_btc_daily_csv(symbol="BTC-EUR", force_download=True, is_optional=True)
    if csv_path_eur is not None:
        try:
            df_eur = load_daily_csv(csv_path_eur)
            df_eur_close = df_eur["Close"].rename("Close_EUR")
            df = df_usd.join(df_eur_close, how="left")
            df["Close_EUR"] = df["Close_EUR"].ffill().bfill()
        except Exception as e:
            print(f"ATTENZIONE: Errore nel caricamento del file BTC-EUR: {e}. Continuo senza dati EUR storici.")
            df = df_usd.copy()
            df["Close_EUR"] = float("nan")
    else:
        df = df_usd.copy()
        df["Close_EUR"] = float("nan")

    df_ind = compute_all_indicators(df)
    df_sig = compute_signals(df_ind)

    latest = df_sig.iloc[-1]
    signal = str(latest["Segnale"])
    risk_level = str(latest.get("Livello_Rischio", "MEDIO"))

    # 3) Prezzo spot live da Coinbase
    try:
        spot_eur = fetch_spot_price("BTC-EUR", timeout_s=10).price
    except Exception:
        print("ATTENZIONE: Impossibile recuperare il prezzo spot BTC-EUR live.")
        spot_eur = None

    try:
        spot_usd = fetch_spot_price("BTC-USD", timeout_s=10).price
    except Exception:
        print("ATTENZIONE: Impossibile recuperare il prezzo spot BTC-USD live.")
        spot_usd = None

    # 4) Eventi: notifica se cambia il segnale notificato o il rischio diventa ALTO
    signal_changed = (state.last_signal is None) or (signal != state.last_signal)
    risk_became_high = (risk_level == "ALTO") and (state.last_risk_level != "ALTO")
    
    must_notify = signal_changed or risk_became_high
    notification_sent = False

    # 5) Invio Telegram
    if must_notify:
        cfg = TelegramConfig(bot_token=bot_token, chat_id=chat_id)
        msg = explain_latest_row(df_sig, price_eur=spot_eur, price_usd=spot_usd)
        try:
            send_telegram_message(cfg, msg)
            notification_sent = True
            print("Notifica Telegram inviata con successo.")
        except Exception as e:
            print(f"Errore nell'invio della notifica Telegram: {e}")
            print("Lo stato notificato non verra aggiornato; il prossimo run riprovera.")
    else:
        print("Nessuna notifica necessaria.")

    # 6) Salva status.json per la dashboard
    status_json_path = project_root / "reports" / "status.json"
    save_status_json(df_sig, price_eur=spot_eur, price_usd=spot_usd, out_path=status_json_path)

    # 7) Salvataggio stato
    state.last_computed_signal = signal
    state.last_computed_risk_level = risk_level
    if notification_sent:
        state.last_signal = signal
        state.last_risk_level = risk_level
    if spot_eur is not None:
        state.last_spot_price = float(spot_eur)
    save_state(state_path, state)
    print("Stato aggiornato e salvato.")


if __name__ == "__main__":
    main()
