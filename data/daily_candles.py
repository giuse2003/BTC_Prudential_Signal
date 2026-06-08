"""
Utility per lavorare con candele giornaliere crypto.
"""

from __future__ import annotations

import pandas as pd


def keep_closed_daily_candles(
    df: pd.DataFrame,
    now_utc: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """
    Mantiene solo le candele giornaliere concluse.

    Yahoo identifica la candela con la data UTC di apertura. La riga con data
    odierna e' ancora in formazione e non deve contribuire ai segnali.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("Il DataFrame deve avere un DatetimeIndex.")

    current = pd.Timestamp.now(tz="UTC") if now_utc is None else pd.Timestamp(now_utc)
    if current.tzinfo is None:
        current = current.tz_localize("UTC")
    else:
        current = current.tz_convert("UTC")

    start_of_today_utc = current.normalize()
    index = df.index
    if index.tz is None:
        cutoff = start_of_today_utc.tz_localize(None)
    else:
        index = index.tz_convert("UTC")
        cutoff = start_of_today_utc

    closed = df.loc[index < cutoff].copy()
    if closed.empty:
        raise ValueError("Nessuna candela giornaliera chiusa disponibile.")
    return closed
