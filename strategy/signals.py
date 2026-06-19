"""
Strategia prudente basata su:
- Trend principale/secondario (SMA200 e SMA50)
- RSI (14)
- Volume relativo (Volume vs VolumeAvg20)
- Distanza dalla SMA200

Output:
- punteggio 0..100
- classificazione (ACQUISTA / MANTIENI / VENDI)
- livello di rischio informativo (BASSO / MEDIO / ALTO)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import CFG
from notifications.telegram import format_monitor_message


def _distance_from_sma200_pct(close: pd.Series, sma200: pd.Series) -> pd.Series:
    """
    Distanza (%): (Close - SMA200) / SMA200 * 100
    """
    # Dove SMA200 è NaN o 0 la distanza diventa NaN/inf -> comparazioni gestiranno a false.
    return (close - sma200) / sma200 * 100.0


def score_rowwise(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola Punteggio totale e componenti.
    Il punteggio è pensato come "somma di condizioni favorevoli".
    """
    df = df.copy()

    close = df["Close"]
    sma50 = df["SMA50"]
    sma200 = df["SMA200"]
    rsi = df["RSI"]
    volume = df["Volume"]
    volume_avg20 = df["VolumeAvg20"]

    distance_pct = _distance_from_sma200_pct(close, sma200)
    df["DistanceFromSMA200_Pct"] = distance_pct

    # Trend principale
    trend_main = (close > sma200).astype(float) * 25.0

    # Trend secondario
    trend_secondary = (sma50 > sma200).astype(float) * 25.0

    # RSI scoring (spec)
    # >= 40: +15
    # 30-40: +10
    # RSI < 30: 0
    rsi_score = np.zeros(len(df), dtype=float)
    rsi_score[rsi >= 40] = 15.0
    rsi_score[(rsi >= 30) & (rsi < 40)] = 10.0
    df["RSI_Score"] = rsi_score

    # Volume scoring (spec: volume odierno > volume medio 20 giorni)
    volume_score = (volume > volume_avg20).astype(float) * 15.0
    df["Volume_Score"] = volume_score

    # Distanza dalla SMA200 (spec)
    # 0% .. 20% => +20
    # > 40% => 0
    # (20% .. 40% => 0 implicito)
    dist_score = np.zeros(len(df), dtype=float)
    dist_score[(distance_pct >= 0) & (distance_pct <= 20)] = 20.0
    # dist_score[distance_pct > 40] resta 0
    df["Distance_Score"] = dist_score

    total = trend_main + trend_secondary + df["RSI_Score"] + df["Volume_Score"] + df["Distance_Score"]
    df["Punteggio"] = total

    return df


def compute_strict_signal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classificazione stretta:
    ACQUISTA se TUTTE le condizioni rialziste sono vere.
    VENDI se il prezzo chiude sotto SMA50 per due giorni consecutivi.
    Altrimenti MANTIENI.
    """
    df = df.copy()

    close = df["Close"]
    sma50 = df["SMA50"]
    sma200 = df["SMA200"]
    rsi = df["RSI"]
    volume = df["Volume"]
    volume_avg20 = df["VolumeAvg20"]
    days = CFG.momentum_days
    close_momentum = df[f"Close_{days}d_ago"]

    buy_cond = (
        (close > sma200) &
        (sma50 > sma200) &
        (rsi >= 40) &
        (close > close_momentum) &
        (volume > volume_avg20)
    )

    below_sma50 = close < sma50
    sell_cond = below_sma50 & below_sma50.shift(1).fillna(False)

    signal = np.full(len(df), "MANTIENI", dtype=object)
    signal[buy_cond] = "ACQUISTA"
    signal[sell_cond] = "VENDI"
    
    df["Segnale"] = signal
    return df


def compute_risk_level(df: pd.DataFrame) -> pd.Series:
    """
    Calcola il livello di rischio (BASSO, MEDIO, ALTO) come informazione ausiliaria.
    """
    close = df["Close"]
    sma50 = df["SMA50"]
    sma200 = df["SMA200"]
    rsi = df["RSI"]
    distance_pct = df["DistanceFromSMA200_Pct"]
    
    # Inizializza a MEDIO
    risk = pd.Series("MEDIO", index=df.index, dtype=object)
    
    # Condizioni per ALTO
    alto_cond = (
        ((close < sma200) & (sma50 < sma200)) |
        (rsi > 70) |
        (distance_pct > 40.0)
    )
    
    # Condizioni per BASSO
    basso_cond = (
        (close > sma200) &
        (sma50 > sma200) &
        (rsi <= 60) &
        (distance_pct <= 20.0)
    )
    
    risk[alto_cond] = "ALTO"
    risk[basso_cond] = "BASSO"
    
    # Gestione valori mancanti
    nan_mask = close.isna() | sma50.isna() | sma200.isna() | rsi.isna()
    risk[nan_mask] = "MEDIO"
    
    return risk


def compute_signals(df_indicators: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline completa:
    - calcola punteggio tecnico (solo per report log, non decide il segnale)
    - classifica con regole strette
    - calcola il livello di rischio informativo
    """
    df = score_rowwise(df_indicators)
    df = compute_strict_signal(df)
    df["Livello_Rischio"] = compute_risk_level(df)
    return df


def format_telegram_message(
    df_with_signals: pd.DataFrame,
    price_eur: float | None = None,
) -> str:
    """
    Produce il messaggio operativo semplificato per Telegram.
    """
    row = df_with_signals.iloc[-1]
    segnale = row.get("Segnale", "N/A")
    rischio = row.get("Livello_Rischio", "MEDIO")

    eur_val = price_eur
    if eur_val is None:
        eur_val = row.get("Close_EUR")
        if pd.isna(eur_val):
            eur_val = None

    return format_monitor_message(
        signal=str(segnale),
        risk_level=str(rischio),
        price_eur=float(eur_val) if eur_val is not None else None,
    )


def explain_latest_row(
    df_with_signals: pd.DataFrame,
    price_eur: float | None = None,
    price_usd: float | None = None,
) -> str:
    """
    Produce una sintesi testuale estesa per il report locale.
    """
    row = df_with_signals.iloc[-1]
    segnale = row.get("Segnale", "N/A")
    rischio = row.get("Livello_Rischio", "MEDIO")
    close_usd = row["Close"]

    usd_val = price_usd if price_usd is not None else float(close_usd)

    eur_val = price_eur
    if eur_val is None:
        eur_val = row.get("Close_EUR")
        if pd.isna(eur_val):
            eur_val = None

    def fmt_curr(val: float | None) -> str:
        if val is None or np.isnan(val):
            return "non disponibile"
        return f"{int(val):,}".replace(",", ".")

    usd_str = f"{fmt_curr(usd_val)} USD"
    eur_str = f"{fmt_curr(eur_val)} EUR" if eur_val is not None else "BTC-EUR non disponibile"

    trend_lungo_txt = "positivo" if usd_val > row["SMA200"] else "negativo"

    rsi = row["RSI"]
    if rsi >= 70:
        rsi_zone = "in zona ipercomprato"
    elif rsi < 30:
        rsi_zone = "in zona ipervenduto"
    else:
        rsi_zone = "in zona neutrale"

    sintesi_lines = [
        f"Trend lungo periodo {trend_lungo_txt}.",
        f"RSI {rsi_zone}.",
    ]
    if segnale == "ACQUISTA":
        sintesi_lines.append("Tutte le conferme rialziste sono allineate.")
    elif segnale == "VENDI":
        sintesi_lines.append("Debolezza tecnica o uscita protettiva confermata.")
    else:
        sintesi_lines.append("Nessuna conferma sufficiente per acquistare.")

    if segnale == "ACQUISTA":
        indicazione = "Accumulare o acquistare posizioni."
    elif segnale == "VENDI":
        indicazione = "Valutare la riduzione del rischio o vendita."
    else:
        indicazione = "Attendere. Nessuna nuova operazione consigliata."

    lines = [
        "BTC MONITOR",
        "",
        f"Segnale: {segnale}",
        f"Rischio: {rischio}",
        "",
        "Prezzo:",
        usd_str,
        eur_str,
        "",
        "Sintesi:",
        "\n".join(sintesi_lines),
        "",
        "Indicazione:",
        indicazione,
    ]

    return "\n".join(lines)

