"""
Job "hourly" pensato per GitHub Actions (piano gratuito).

Comportamento:
- Scarica/aggiorna dati giornalieri BTC-USD (Yahoo Finance) e calcola indicatori giornalieri.
- Calcola segnale "di regime" (prudente).
- Legge prezzo spot "live" da Coinbase in EUR.
- Invia DAILY su nuova candela se cambia il segnale.
- Invia LIVE se le condizioni aggregate CoinGecko restano variate per almeno 30 minuti.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from data.fetch_yahoo import fetch_btc_daily_csv, load_daily_csv
from data.daily_candles import keep_closed_daily_candles
from indicators.technical_indicators import compute_all_indicators
from live.coinbase import fetch_spot_price
from live.coingecko import fetch_btc_market
from notifications.telegram import TelegramConfig, send_telegram_message
from strategy.signals import (
    build_live_signal_frame,
    compute_signals,
    condition_key_from_statuses,
    condition_state_key,
    format_condition_message,
    format_telegram_message,
    live_condition_statuses,
    signal_from_condition_statuses,
)
from state.state_store import MonitorState, load_state, save_state
from reports.generate import save_chart_data_json, save_live_status_json, save_status_json


LIVE_STABILITY_MINUTES = 30
LIVE_ALERT_COOLDOWN_HOURS = 2


def should_notify(state: MonitorState, signal: str, conditions_key: str) -> tuple[bool, str]:
    if state.last_signal is None or state.last_conditions_key is None:
        return False, "baseline iniziale salvata senza notifica"

    if signal != state.last_signal:
        return True, f"segnale cambiato: {state.last_signal} -> {signal}"

    if conditions_key != state.last_conditions_key:
        return True, "condizioni operative cambiate"

    return False, "segnale e condizioni invariati"


def _parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def should_send_live_alert(
    state: MonitorState,
    live_conditions_key: str,
    now_utc: datetime,
) -> tuple[bool, str]:
    now_iso = now_utc.isoformat()

    if state.last_live_conditions_key is None:
        state.last_live_conditions_key = live_conditions_key
        state.live_pending_conditions_key = None
        state.live_pending_since_utc = None
        return False, "baseline LIVE salvata senza notifica"

    if live_conditions_key != state.last_live_conditions_key:
        state.last_live_conditions_key = live_conditions_key
        state.live_pending_conditions_key = live_conditions_key
        state.live_pending_since_utc = now_iso
        return False, "condizioni LIVE variate; attendo stabilita 30 minuti"

    if state.live_pending_conditions_key != live_conditions_key:
        return False, "condizioni LIVE invariate"

    pending_since = _parse_iso_utc(state.live_pending_since_utc)
    if pending_since is None:
        state.live_pending_since_utc = now_iso
        return False, "stabilita LIVE inizializzata"

    stable_for = now_utc - pending_since
    if stable_for < timedelta(minutes=LIVE_STABILITY_MINUTES):
        minutes = int(stable_for.total_seconds() // 60)
        return False, f"condizioni LIVE stabili da {minutes} minuti; attendo 30 minuti"

    last_alert_at = _parse_iso_utc(state.last_live_alert_sent_at_utc)
    if (
        state.last_live_alert_conditions_key == live_conditions_key
        and last_alert_at is not None
        and now_utc - last_alert_at < timedelta(hours=LIVE_ALERT_COOLDOWN_HOURS)
    ):
        return False, "allerta LIVE identica gia inviata nelle ultime 2 ore"

    return True, "condizioni LIVE variate e stabili da almeno 30 minuti"


def main() -> None:
    github_event_name = os.environ.get("GITHUB_EVENT_NAME", "").strip()
    is_manual_run = github_event_name == "workflow_dispatch"
    now_utc = datetime.now(timezone.utc)
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
    expected_closed_candle_date = (now_utc.date() - timedelta(days=1)).isoformat()
    should_poll_yahoo_now = now_utc.minute == 30 or is_manual_run
    force_daily_download = (
        state.last_processed_candle_date != expected_closed_candle_date
        and should_poll_yahoo_now
    )
    if force_daily_download:
        print(f"Controllo Yahoo per cercare la candela chiusa attesa: {expected_closed_candle_date}")
    elif state.last_processed_candle_date != expected_closed_candle_date:
        print(
            f"Candela attesa {expected_closed_candle_date} non ancora processata. "
            "Questo run aggiorna il LIVE; Yahoo verra forzato al minuto 30."
        )
    else:
        print(
            f"Candela attesa {expected_closed_candle_date} gia processata. "
            "Uso i dati locali/cache senza forzare Yahoo."
        )

    # 2) Dati giornalieri + indicatori (con doppia valuta USD/EUR)
    csv_path_usd = fetch_btc_daily_csv(symbol="BTC-USD", force_download=force_daily_download, is_optional=False)
    df_usd = keep_closed_daily_candles(load_daily_csv(csv_path_usd))
    
    csv_path_eur = fetch_btc_daily_csv(symbol="BTC-EUR", force_download=force_daily_download, is_optional=True)
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
    latest_candle_date = df_sig.index[-1].strftime("%Y-%m-%d")
    signal = str(latest["Segnale"])
    risk_level = str(latest.get("Livello_Rischio", "MEDIO"))
    conditions_key = condition_state_key(df_sig)
    print(f"Ultima candela giornaliera chiusa: {latest_candle_date}")
    print(f"Segnale calcolato: {signal}")
    print(f"Rischio calcolato: {risk_level}")
    print(f"Condizioni calcolate: {conditions_key}")
    new_candle_available = latest_candle_date != state.last_processed_candle_date
    if new_candle_available:
        print(
            "Nuova candela da processare: "
            f"{state.last_processed_candle_date or 'nessuna precedente'} -> {latest_candle_date}"
        )
    else:
        print(f"Candela {latest_candle_date} gia processata. Nessuna notifica o ricalcolo operativo.")

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

    # 4) Eventi:
    # - workflow manuale: invia sempre, come una richiesta esplicita /segnale
    # - workflow schedulato: processa una candela giornaliera una sola volta
    #   e invia DAILY se cambia almeno una condizione o il segnale finale.
    if new_candle_available:
        scheduled_notify, notify_reason = should_notify(state, signal, conditions_key)
    else:
        scheduled_notify, notify_reason = False, "candela gia processata"
    must_notify = is_manual_run or scheduled_notify
    notification_sent = False
    if is_manual_run:
        notify_reason = "richiesta manuale workflow_dispatch"
    print(f"Motivo decisione Telegram: {notify_reason}")

    # 5) Invio Telegram
    if must_notify:
        cfg = TelegramConfig(bot_token=bot_token, chat_id=chat_id)
        msg = format_telegram_message(df_sig, price_eur=spot_eur, title="BTC Signal Guard DAILY!")
        try:
            send_telegram_message(cfg, msg)
            notification_sent = True
            print("Notifica Telegram inviata con successo.")
        except Exception as e:
            print(f"Errore nell'invio della notifica Telegram: {e}")
            print("Lo stato notificato non verra aggiornato; il prossimo run riprovera.")
    else:
        print("Nessuna notifica necessaria.")

    try:
        live_market = fetch_btc_market(timeout_s=10)
        live_df_sig = build_live_signal_frame(
            df,
            live_price_usd=live_market.price_usd,
            live_volume_24h=live_market.volume_24h_usd,
            live_time_utc=pd.Timestamp(now_utc),
        )
        live_buy_statuses, live_sell_statuses = live_condition_statuses(live_df_sig)
        live_conditions_key = condition_key_from_statuses(live_buy_statuses, live_sell_statuses)
        live_signal = signal_from_condition_statuses(live_buy_statuses, live_sell_statuses)
        print(f"Segnale LIVE calcolato: {live_signal}")
        print(f"Condizioni LIVE calcolate: {live_conditions_key}")
        print(f"Prezzo LIVE aggregato CoinGecko: {live_market.price_usd:.2f} USD")
        print(f"Volume LIVE aggregato 24h CoinGecko: {live_market.volume_24h_usd:.2f}")
        save_live_status_json(
            signal=live_signal,
            price_usd=live_market.price_usd,
            price_eur=live_market.price_eur,
            volume_24h_usd=live_market.volume_24h_usd,
            buy_statuses=live_buy_statuses,
            sell_statuses=live_sell_statuses,
            out_path=project_root / "reports" / "live-status.json",
        )

        if not is_manual_run:
            live_must_notify, live_notify_reason = should_send_live_alert(
                state,
                live_conditions_key,
                now_utc,
            )
            print(f"Motivo decisione Telegram LIVE: {live_notify_reason}")

            if live_must_notify:
                cfg = TelegramConfig(bot_token=bot_token, chat_id=chat_id)
                live_msg = format_condition_message(
                    signal=live_signal,
                    price_eur=live_market.price_eur if live_market.price_eur is not None else spot_eur,
                    buy_statuses=live_buy_statuses,
                    sell_statuses=live_sell_statuses,
                    title="BTC Signal Guard LIVE!",
                )
                try:
                    send_telegram_message(cfg, live_msg)
                    state.last_live_alert_conditions_key = live_conditions_key
                    state.last_live_alert_sent_at_utc = now_utc.isoformat()
                    state.live_pending_conditions_key = None
                    state.live_pending_since_utc = None
                    print("Notifica Telegram LIVE inviata con successo.")
                except Exception as e:
                    print(f"Errore nell'invio della notifica Telegram LIVE: {e}")
                    print("L'allerta LIVE non verra marcata come inviata; il prossimo run riprovera.")
        else:
            print("Workflow manuale: LIVE salvato senza inviare allerta automatica.")
    except Exception as e:
        print(f"LIVE non calcolabile con dati aggregati CoinGecko: {e}")

    # 6) Salva status.json per la dashboard
    status_json_path = project_root / "reports" / "status.json"
    save_status_json(df_sig, price_eur=spot_eur, price_usd=spot_usd, out_path=status_json_path)
    save_chart_data_json(df_sig, out_path=project_root / "reports" / "chart-data.json")

    # 7) Salvataggio stato
    if new_candle_available:
        state.last_computed_signal = signal
        state.last_computed_conditions_key = conditions_key
        state.last_computed_risk_level = risk_level

    candle_processed = new_candle_available and (not must_notify or notification_sent)

    if candle_processed:
        state.last_processed_candle_date = latest_candle_date

    if candle_processed:
        state.last_signal = signal
        state.last_conditions_key = conditions_key
        state.last_risk_level = risk_level
    if spot_eur is not None:
        state.last_spot_price = float(spot_eur)
    save_state(state_path, state)
    print("Stato aggiornato e salvato.")


if __name__ == "__main__":
    main()
