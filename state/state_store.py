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
        "last_processed_candle_date": state.last_processed_candle_date,
        "last_live_conditions_key": state.last_live_conditions_key,
        "live_pending_conditions_key": state.live_pending_conditions_key,
        "live_pending_since_utc": state.live_pending_since_utc,
        "last_live_alert_conditions_key": state.last_live_alert_conditions_key,
        "last_live_alert_sent_at_utc": state.last_live_alert_sent_at_utc,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

