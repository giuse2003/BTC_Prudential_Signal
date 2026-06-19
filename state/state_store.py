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
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

