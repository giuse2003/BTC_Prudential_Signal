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
    # ultimo segnale operativo (es. "ACQUISTO", "RIDURRE ESPOSIZIONE", ...)
    last_signal: str | None = None
    # ultima price osservata dal job (spot Coinbase)
    last_spot_price: float | None = None
    # ultimo "livello" attraversato/triggerato, per ridurre spam (opzionale)
    last_level_event: str | None = None


def load_state(path: str | Path) -> MonitorState:
    path = Path(path)
    if not path.exists():
        return MonitorState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return MonitorState(
            last_signal=raw.get("last_signal"),
            last_spot_price=raw.get("last_spot_price"),
            last_level_event=raw.get("last_level_event"),
        )
    except Exception:
        return MonitorState()


def save_state(path: str | Path, state: MonitorState) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_signal": state.last_signal,
        "last_spot_price": state.last_spot_price,
        "last_level_event": state.last_level_event,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

