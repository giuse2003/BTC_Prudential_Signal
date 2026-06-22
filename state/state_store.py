"""
Persistenza di stato tra run (per evitare spam).

Su GitHub Actions non abbiamo un filesystem persistente.
Soluzione: cache Actions su una cartella di stato (vedi workflow).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MonitorState:
    # ultimo segnale notificato con successo (es. "ACQUISTA", "MANTIENI", "VENDI")
    last_signal: str | None = None
    # ultima impronta delle condizioni notificata con successo
    last_conditions_key: str | None = None
    # ultima price osservata dal job (spot Coinbase)
    last_spot_price: float | None = None
    # ultimo "livello" attraversato/triggerato, per ridurre spam (opzionale)
    last_level_event: str | None = None
    # ultimo livello di rischio notificato con successo
    last_risk_level: str | None = None
    # ultimo segnale calcolato, anche se la notifica Telegram fallisce
    last_computed_signal: str | None = None
    # ultima impronta delle condizioni calcolata, anche se la notifica Telegram fallisce
    last_computed_conditions_key: str | None = None
    # ultimo livello di rischio calcolato, anche se la notifica Telegram fallisce
    last_computed_risk_level: str | None = None
    # ultima candela giornaliera chiusa gia processata (YYYY-MM-DD)
    last_processed_candle_date: str | None = None
    # ultima impronta condizioni LIVE osservata
    last_live_conditions_key: str | None = None
    # impronta LIVE candidata, in attesa che resti stabile
    live_pending_conditions_key: str | None = None
    # inizio stabilita della condizione LIVE candidata (ISO UTC)
    live_pending_since_utc: str | None = None
    # ultima impronta LIVE notificata
    last_live_alert_conditions_key: str | None = None
    # timestamp ultima allerta LIVE inviata (ISO UTC)
    last_live_alert_sent_at_utc: str | None = None


def load_state(path: str | Path) -> MonitorState:
    path = Path(path)
    if not path.exists():
        return MonitorState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return MonitorState(
            last_signal=raw.get("last_signal"),
            last_conditions_key=raw.get("last_conditions_key"),
            last_spot_price=raw.get("last_spot_price"),
            last_level_event=raw.get("last_level_event"),
            last_risk_level=raw.get("last_risk_level"),
            last_computed_signal=raw.get("last_computed_signal"),
            last_computed_conditions_key=raw.get("last_computed_conditions_key"),
            last_computed_risk_level=raw.get("last_computed_risk_level"),
            last_processed_candle_date=raw.get("last_processed_candle_date"),
            last_live_conditions_key=raw.get("last_live_conditions_key"),
            live_pending_conditions_key=raw.get("live_pending_conditions_key"),
            live_pending_since_utc=raw.get("live_pending_since_utc"),
            last_live_alert_conditions_key=raw.get("last_live_alert_conditions_key"),
            last_live_alert_sent_at_utc=raw.get("last_live_alert_sent_at_utc"),
        )
    except Exception:
        return MonitorState()


def save_state(path: str | Path, state: MonitorState) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_signal": state.last_signal,
        "last_conditions_key": state.last_conditions_key,
        "last_spot_price": state.last_spot_price,
        "last_level_event": state.last_level_event,
        "last_risk_level": state.last_risk_level,
        "last_computed_signal": state.last_computed_signal,
        "last_computed_conditions_key": state.last_computed_conditions_key,
        "last_computed_risk_level": state.last_computed_risk_level,
        "last_processed_candle_date": state.last_processed_candle_date,
        "last_live_conditions_key": state.last_live_conditions_key,
        "live_pending_conditions_key": state.live_pending_conditions_key,
        "live_pending_since_utc": state.live_pending_since_utc,
        "last_live_alert_conditions_key": state.last_live_alert_conditions_key,
        "last_live_alert_sent_at_utc": state.last_live_alert_sent_at_utc,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

