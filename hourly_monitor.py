"""
Job "hourly" pensato per GitHub Actions (piano gratuito).

Comportamento:
- Scarica/aggiorna dati giornalieri BTC-USD (Yahoo Finance) e calcola indicatori giornalieri.
- Calcola segnale "di regime" (prudente).
- Legge prezzo spot "live" da Coinbase in EUR.
- Invia notifica Telegram solo se cambia il segnale o cambia almeno una condizione operativa.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from data.fetch_yahoo import fetch_btc_daily_csv, load_daily_csv
from data.daily_candles import keep_closed_daily_candles
from indicators.technical_indicators import compute_all_indicators
from live.coinbase import fetch_spot_price
from notifications.telegram import TelegramConfig, send_telegram_message
from strategy.signals import compute_signals, condition_state_key, format_telegram_message
from state.state_store import MonitorState, load_state, save_state
from reports.generate import save_status_json


def should_notify(state: MonitorState, signal: str, conditions_key: str) -> tuple[bool, str]:
    if state.last_signal is None or state.last_conditions_key is None:
        return False, "baseline iniziale salvata senza notifica"

    if signal != state.last_signal:
        return True, f"segnale cambiato: {state.last_signal} -> {signal}"

    if conditions_key != state.last_conditions_key:
        return True, "condizioni operative cambiate"

    return False, "segnale e condizioni invariati"


def main() -> None:
    github_event_name = os.environ.get("GITHUB_EVENT_NAME", "").strip()
    print(f"Evento GitHub rilevato: {github_event_name or 'non disponibile'}")

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
    df_usd = keep_closed_daily_candles(load_daily_csv(csv_path_usd))
    
    csv_path_eur = fetch_btc_daily_csv(symbol="BTC-EUR", force_download=True, is_optional=True)
    if csv_path_eur is not None:
        try:
            df_eur = keep_closed_daily_candles(load_daily_csv(csv_path_eur))
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
    conditions_key = condition_state_key(df_sig)
    print(f"Ultima candela giornaliera chiusa: {df_sig.index[-1]:%Y-%m-%d}")
    print(f"Segnale calcolato: {signal}")
    print(f"Rischio calcolato: {risk_level}")
    print(f"Condizioni calcolate: {conditions_key}")

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

    # 4) Eventi: notifica solo se cambia il segnale o cambia una condizione operativa.
    must_notify, notify_reason = should_notify(state, signal, conditions_key)
    notification_sent = False
    print(f"Motivo decisione Telegram: {notify_reason}")

    # 5) Invio Telegram
    if must_notify:
        cfg = TelegramConfig(bot_token=bot_token, chat_id=chat_id)
        msg = format_telegram_message(df_sig, price_eur=spot_eur)
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
    state.last_computed_conditions_key = conditions_key
    state.last_computed_risk_level = risk_level
    if notification_sent or state.last_signal is None or state.last_conditions_key is None:
        state.last_signal = signal
        state.last_conditions_key = conditions_key
        state.last_risk_level = risk_level
    if spot_eur is not None:
        state.last_spot_price = float(spot_eur)
    save_state(state_path, state)
    print("Stato aggiornato e salvato.")


if __name__ == "__main__":
    main()
