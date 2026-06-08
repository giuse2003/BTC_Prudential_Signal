"""
Configurazione centralizzata.

Obiettivo:
- rendere facile modificare finestre (SMA, RSI, ecc.)
- rendere facile estendere la logica futura (on-chain, Fear & Greed, ecc.)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    # Intervallo dati
    start_date: str = "2015-01-01"
    end_date: str = "today"

    # Serie usata per i segnali (Yahoo Finance)
    # "BTC-USD" perché è l'indicatore standard di trading su Yahoo.
    # Se vuoi cambiare quote a EUR/USD o altre, puoi farlo qui.
    symbol: str = "BTC-USD"

    # Indicatori tecnici
    sma_fast: int = 50
    sma_slow: int = 200
    rsi_period: int = 14
    vol_avg_period: int = 20
    atr_period: int = 14
    periods_per_year: int = 365  # Bitcoin scambia 7 giorni su 7
    weeks_52_days: int = 365
    momentum_days: int = 7    # Confronto prezzo con 7 giorni fa

    # Punteggio (0..100)
    # Nota: i pesi sono implementati direttamente nella strategia per chiarezza.

    # Esposizione prudente (mappatura segnale -> peso capitale).
    # MANTIENI usa NaN per indicare: conserva l'esposizione precedente.
    # - ACQUISTA -> 100%
    # - MANTIENI -> esposizione precedente
    # - VENDI -> 0%
    exposure_map: dict[str, float] = None  # impostato in __post_init__

    def __post_init__(self) -> None:
        # dataclass frozen => usiamo object.__setattr__
        object.__setattr__(
            self,
            "exposure_map",
            {
                "ACQUISTA": 1.0,
                "MANTIENI": float("nan"),  # NaN indica di mantenere l'esposizione precedente
                "VENDI": 0.0,
            },
        )


CFG = Config()

