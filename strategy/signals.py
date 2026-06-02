"""
Strategia prudente basata su:
- Trend principale/secondario (SMA200 e SMA50)
- RSI (14)
- Volume relativo (Volume vs VolumeAvg20)
- Distanza dalla SMA200

Output:
- punteggio 0..100
- classificazione (EVITARE / ACCUMULO GRADUALE / ACQUISTO / ACQUISTO FORTE)
- regole di vendita (RIDURRE ESPOSIZIONE) con priorità assoluta
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import CFG


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
    # 40-65: +15
    # 30-40: +10
    # RSI > 75: 0
    # RSI < 30: 0
    rsi_score = np.zeros(len(df), dtype=float)
    rsi_score[(rsi >= 40) & (rsi <= 65)] = 15.0
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
    VENDI / RIDUCI ESPOSIZIONE se TUTTE le condizioni ribassiste sono vere.
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
        (rsi >= 40) & (rsi <= 65) &
        (close > close_momentum) &
        (volume > volume_avg20)
    )

    sell_cond = (
        (close < sma200) &
        (sma50 < sma200) &
        (rsi < 35) &
        (close < close_momentum) &
        (volume > volume_avg20)
    )

    signal = np.full(len(df), "MANTIENI", dtype=object)
    signal[buy_cond] = "ACQUISTA"
    signal[sell_cond] = "VENDI / RIDUCI ESPOSIZIONE"
    
    df["Segnale"] = signal
    return df


def compute_signals(df_indicators: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline completa:
    - calcola punteggio tecnico (solo per report log, non decide il segnale)
    - classifica con regole strette
    """
    df = score_rowwise(df_indicators)
    df = compute_strict_signal(df)
    
    # Estensione futura (on-chain) - placeholder
    df = apply_onchain_filters_placeholder(df)

    return df


def apply_onchain_filters_placeholder(df_with_signals: pd.DataFrame) -> pd.DataFrame:
    """
    Stub per filtri on-chain.
    """
    return df_with_signals


def explain_latest_row(df_with_signals: pd.DataFrame, price_eur: float | None = None) -> str:
    """
    Produce una sintesi testuale chiara (stile discorsivo) per Telegram.
    Non espone dettagli tecnici superflui (se non indispensabili).
    """
    row = df_with_signals.iloc[-1]
    segnale = row.get("Segnale", "N/A")
    close_usd = row["Close"]
    
    # Trend lungo/medio (rispetto a SMA200 e SMA50 vs SMA200)
    trend_lungo = "positivo" if close_usd > row["SMA200"] else "negativo"
    trend_medio = "positivo" if row["SMA50"] > row["SMA200"] else "negativo"
    
    # RSI check
    rsi = row["RSI"]
    if rsi < 30:
        rsi_desc = f"{rsi:.1f} — mercato ipervenduto"
    elif rsi < 40:
        rsi_desc = f"{rsi:.1f} — mercato debole"
    elif rsi <= 65:
        rsi_desc = f"{rsi:.1f} — zona neutrale/costruttiva"
    else:
        rsi_desc = f"{rsi:.1f} — mercato ipercomprato"

    # Volume check
    vol_desc = "confermano la direzione (sopra media)" if row["Volume"] > row["VolumeAvg20"] else "non confermano (sotto media)"
    
    # Prezzo EUR string (se disponibile)
    prezzo_str = f"{price_eur:,.2f} EUR".replace(",", "X").replace(".", ",").replace("X", ".") if price_eur else f"{close_usd:,.2f} USD"

    lines = []
    lines.append("BTC MONITOR")
    lines.append("")
    lines.append(f"Segnale: {segnale}")
    lines.append("")
    lines.append(f"Prezzo BTC: {prezzo_str}")
    lines.append("")
    lines.append("Situazione:")
    lines.append(f"- Trend lungo periodo: {trend_lungo}")
    lines.append(f"- Trend medio periodo: {trend_medio}")
    lines.append(f"- RSI: {rsi_desc}")
    lines.append(f"- Volumi: {vol_desc}")
    lines.append("")
    lines.append("Indicazione:")
    
    if segnale == "ACQUISTA":
        lines.append("Tutte le conferme rialziste sono allineate.")
        lines.append("Condizioni favorevoli per accumulare o comprare.")
    elif segnale == "VENDI / RIDUCI ESPOSIZIONE":
        lines.append("Il mercato mostra forte debolezza e i volumi confermano il trend ribassista.")
        lines.append("Valutare la riduzione del rischio.")
    else:
        lines.append("Non acquistare ora.")
        lines.append("Se hai già BTC, valuta di mantenere o ridurre solo se arrivano ulteriori conferme ribassiste.")
        lines.append("Nessun nuovo acquisto finché il trend non migliora.")

    return "\n".join(lines)

