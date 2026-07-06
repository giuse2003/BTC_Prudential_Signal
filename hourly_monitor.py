"""
Job "hourly" pensato per GitHub Actions (piano gratuito).

Comportamento:
- Scarica/aggiorna dati giornalieri BTC-USD (Yahoo Finance) e calcola indicatori giornalieri.
- Calcola segnale "di regime" (prudente).
- Legge prezzo spot "live" da Coinbase in EUR.
- Invia DAILY su nuova candela se cambia il segnale.
- Invia LIVE se le condizioni aggregate CoinGecko restano variate per almeno 10 minuti.
"""

from __future__ import annotations

import os
import requests
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from telegram_subscribers import SupabaseSubscriberStore

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


LIVE_STABILITY_MINUTES = 10
LIVE_ALERT_COOLDOWN_HOURS = 2


def should_notify(state: MonitorState, signal: str, conditions_key: str) -> tuple[bool, str]:
    if state.last_signal is None or state.last_conditions_key is None:
        return False, "baseline iniziale salvata senza notifica"

    if signal != state.last_signal:
        return True, f"segnale cambiato: {state.last_signal} -> {signal}"

    if conditions_key != state.last_conditions_key:
        return True, "condizioni operative cambiate"

    return False, "segnale e condizioni invariati"


def should_force_daily_download(
    state: MonitorState,
    expected_closed_candle_date: str,
    is_manual_run: bool = False,
) -> bool:
    """
    Forza Yahoo finche la candela giornaliera attesa non risulta processata.

    I run schedulati avvengono ogni 10 minuti. Limitare il download al solo
    minuto 30 puo lasciare dashboard e grafico bloccati se quel tentativo
    fallisce o Yahoo non ha ancora pubblicato dati consistenti.
    """
    return is_manual_run or state.last_processed_candle_date != expected_closed_candle_date


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
        return False, f"condizioni LIVE variate; attendo stabilita {LIVE_STABILITY_MINUTES} minuti"

    if state.live_pending_conditions_key != live_conditions_key:
        return False, "condizioni LIVE invariate"

    pending_since = _parse_iso_utc(state.live_pending_since_utc)
    if pending_since is None:
        state.live_pending_since_utc = now_iso
        return False, "stabilita LIVE inizializzata"

    stable_for = now_utc - pending_since
    if stable_for < timedelta(minutes=LIVE_STABILITY_MINUTES):
        minutes = int(stable_for.total_seconds() // 60)
        return False, f"condizioni LIVE stabili da {minutes} minuti; attendo {LIVE_STABILITY_MINUTES} minuti"

    last_alert_at = _parse_iso_utc(state.last_live_alert_sent_at_utc)
    if (
        state.last_live_alert_conditions_key == live_conditions_key
        and last_alert_at is not None
        and now_utc - last_alert_at < timedelta(hours=LIVE_ALERT_COOLDOWN_HOURS)
    ):
        return False, "allerta LIVE identica gia inviata nelle ultime 2 ore"

    return True, f"condizioni LIVE variate e stabili da almeno {LIVE_STABILITY_MINUTES} minuti"


def broadcast_to_subscribers(
    bot_token: str,
    supabase_url: str,
    supabase_key: str,
    text: str,
    excluded_chat_ids: set[str] | None = None,
) -> None:
    """
    Invia il messaggio a tutti gli iscritti attivi memorizzati su Supabase.
    Gestisce i fallimenti e disattiva chi ha bloccato il bot.
    """
    store = SupabaseSubscriberStore(supabase_url, supabase_key)
    try:
        subscribers = store.get_active_subscribers()
    except Exception as e:
        print(f"Errore nel recupero degli iscritti da Supabase: {e}")
        return

    print(f"Avvio broadcast a {len(subscribers)} iscritti attivi...")

    excluded_chat_ids = excluded_chat_ids or set()
    sent_count = 0

    for sub in subscribers:
        sub_chat_id = sub.telegram_chat_id
        if str(sub_chat_id) in excluded_chat_ids:
            print(f"Salto chat_id {sub_chat_id}: gia notificato direttamente.")
            continue

        cfg = TelegramConfig(bot_token=bot_token, chat_id=str(sub_chat_id))
        
        # Ritardo per non superare il rate limit (max 30 msg/sec)
        if sent_count > 0:
            time.sleep(0.05)
            
        try:
            send_telegram_message(cfg, text)
            sent_count += 1
            print(f"Notifica inviata con successo a chat_id {sub_chat_id}")
            try:
                store.update_delivery_status(sub_chat_id, success=True)
            except Exception as db_err:
                print(f"Errore nell'aggiornamento dello stato di consegna su Supabase per chat_id {sub_chat_id}: {db_err}")
        except requests.exceptions.HTTPError as err:
            response = err.response
            is_block = False
            err_msg = str(err)
            if response is not None:
                err_msg = f"HTTP {response.status_code}: {response.text}"
                if response.status_code == 403:
                    is_block = True
                    
            print(f"Errore di invio a chat_id {sub_chat_id} (blocco={is_block}): {err_msg}")
            try:
                store.update_delivery_status(sub_chat_id, success=False, error_msg=err_msg, block_detected=is_block)
            except Exception as db_err:
                print(f"Errore nell'aggiornamento dello stato di fallimento su Supabase per chat_id {sub_chat_id}: {db_err}")
        except Exception as e:
            err_msg = str(e)
            print(f"Errore generico di invio a chat_id {sub_chat_id}: {err_msg}")
            try:
                store.update_delivery_status(sub_chat_id, success=False, error_msg=err_msg, block_detected=False)
            except Exception as db_err:
                print(f"Errore nell'aggiornamento dello stato di fallimento su Supabase per chat_id {sub_chat_id}: {db_err}")


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

    # Supabase secrets
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    project_root = Path(__file__).resolve().parent
    state_path = project_root / ".state" / "state.json"

    # 1) Stato precedente
    state = load_state(state_path)
    expected_closed_candle_date = (now_utc.date() - timedelta(days=1)).isoformat()
    force_daily_download = should_force_daily_download(
        state,
        expected_closed_candle_date,
        is_manual_run=is_manual_run,
    )
    if force_daily_download:
        print(f"Controllo Yahoo per cercare la candela chiusa attesa: {expected_closed_candle_date}")
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
            print("Notifica Telegram all'amministratore inviata con successo.")
        except Exception as e:
            print(f"Errore nell'invio della notifica Telegram all'amministratore: {e}")
            print("Lo stato notificato non verra aggiornato; il prossimo run riprovera.")

        if supabase_url and supabase_key:
            try:
                broadcast_to_subscribers(
                    bot_token,
                    supabase_url,
                    supabase_key,
                    msg,
                    excluded_chat_ids={str(chat_id)},
                )
            except Exception as e:
                print(f"Errore durante il broadcast DAILY: {e}")
        else:
            print("Supabase non configurato. Salto il broadcast DAILY.")
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
        live_latest = live_df_sig.iloc[-1]
        save_live_status_json(
            signal=live_signal,
            price_usd=live_market.price_usd,
            price_eur=live_market.price_eur,
            volume_24h_usd=live_market.volume_24h_usd,
            buy_statuses=live_buy_statuses,
            sell_statuses=live_sell_statuses,
            rsi=float(live_latest.get("RSI", float("nan"))),
            sma50=float(live_latest.get("SMA50", float("nan"))),
            sma200=float(live_latest.get("SMA200", float("nan"))),
            atr=float(live_latest.get("ATR", float("nan"))),
            risk_level=str(live_latest.get("Livello_Rischio", "MEDIO")),
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
                    print("Notifica Telegram LIVE all'amministratore inviata con successo.")
                except Exception as e:
                    print(f"Errore nell'invio della notifica Telegram LIVE all'amministratore: {e}")
                    print("L'allerta LIVE non verra marcata come inviata; il prossimo run riprovera.")

                if supabase_url and supabase_key:
                    try:
                        broadcast_to_subscribers(
                            bot_token,
                            supabase_url,
                            supabase_key,
                            live_msg,
                            excluded_chat_ids={str(chat_id)},
                        )
                    except Exception as e:
                        print(f"Errore durante il broadcast LIVE: {e}")
                else:
                    print("Supabase non configurato. Salto il broadcast LIVE.")
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
