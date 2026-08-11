"""Monitor schedulato: pubblicazione coerente e notifiche LIVE PREVIEW."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from notifications.telegram import TelegramConfig, send_telegram_message
from pipeline import run_pipeline
from state.state_store import MonitorState, load_state, save_state
from strategy.signals import format_condition_message
from telegram_subscribers import SupabaseSubscriberStore

LIVE_STABILITY_MINUTES = 10
LIVE_ALERT_COOLDOWN_HOURS = 2


def should_force_daily_download(
    state: MonitorState,
    expected_closed_candle_date: str,
    is_manual_run: bool = False,
) -> bool:
    """Compatibilita': un run manuale puo ricostruire tutta la cache Coinbase."""
    return is_manual_run


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
        return False, f"condizioni LIVE stabili da {minutes} minuti"
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
    store = SupabaseSubscriberStore(supabase_url, supabase_key)
    try:
        subscribers = store.get_active_subscribers()
    except Exception as exc:
        print(f"Errore nel recupero degli iscritti: {exc}")
        return
    excluded = excluded_chat_ids or set()
    for index, subscriber in enumerate(subscribers):
        stored_chat_id = subscriber.telegram_chat_id
        chat_id = str(stored_chat_id)
        if chat_id in excluded:
            continue
        if index:
            time.sleep(0.05)
        try:
            send_telegram_message(TelegramConfig(bot_token=bot_token, chat_id=chat_id), text)
            store.update_delivery_status(stored_chat_id, success=True)
        except requests.exceptions.HTTPError as exc:
            blocked = exc.response is not None and exc.response.status_code == 403
            response = exc.response
            error_message = (
                f"HTTP {response.status_code}: {response.text}"
                if response is not None
                else str(exc)
            )
            store.update_delivery_status(
                stored_chat_id,
                success=False,
                error_msg=error_message,
                block_detected=blocked,
            )
        except Exception as exc:
            print(f"Invio a {chat_id} non riuscito: {exc}")
            store.update_delivery_status(
                stored_chat_id,
                success=False,
                error_msg=str(exc),
                block_detected=False,
            )


def main() -> None:
    now_utc = datetime.now(timezone.utc)
    is_manual = os.environ.get("GITHUB_EVENT_NAME", "").strip() == "workflow_dispatch"
    root = Path(__file__).resolve().parent
    state_path = root / ".state" / "state.json"
    state = load_state(state_path)

    result = run_pipeline(
        output_dir=root / "reports",
        refresh_all=should_force_daily_download(
            state,
            (now_utc.date() - timedelta(days=1)).isoformat(),
            is_manual_run=is_manual,
        ),
    )
    print(f"Run pubblicato: {result.run_id}")
    print(f"DAILY {result.candle_date}: {result.daily_action}")
    print(f"LIVE PREVIEW: {result.live_action} ({result.live_conditions_key})")

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    admin_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not is_manual:
        must_notify, reason = should_send_live_alert(
            state,
            result.live_conditions_key,
            now_utc,
        )
        print(f"Decisione notifica LIVE: {reason}")
        if must_notify and bot_token and admin_chat_id:
            message = format_condition_message(
                signal=result.live_action,
                price_eur=result.price_eur,
                buy_statuses=result.buy_statuses,
                sell_statuses=result.sell_statuses,
                title="BTC-USD Signal - LIVE PREVIEW",
            )
            message = "\n".join(
                [
                    message,
                    "",
                    "🔗 <a href=\"https://giuse2003.github.io/BTC_Prudential_Signal/\">Apri la Dashboard</a>",
                ]
            )
            send_telegram_message(
                TelegramConfig(bot_token=bot_token, chat_id=admin_chat_id),
                message,
            )
            state.last_live_alert_conditions_key = result.live_conditions_key
            state.last_live_alert_sent_at_utc = now_utc.isoformat()
            state.live_pending_conditions_key = None
            state.live_pending_since_utc = None
            if supabase_url and supabase_key:
                broadcast_to_subscribers(
                    bot_token,
                    supabase_url,
                    supabase_key,
                    message,
                    excluded_chat_ids={admin_chat_id},
                )

    state.last_processed_candle_date = result.candle_date
    save_state(state_path, state)
    print("Stato monitor salvato dopo la pubblicazione completa.")


if __name__ == "__main__":
    main()
