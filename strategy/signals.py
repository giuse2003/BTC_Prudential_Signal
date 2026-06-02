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


def classify_by_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte Punteggio 0..100 nel segnale di accumulo/acquisto.
    """
    df = df.copy()
    score = df["Punteggio"].astype(float)

    signal = np.full(len(df), "EVITARE", dtype=object)
    signal[(score >= 40) & (score <= 69)] = "ACCUMULO GRADUALE"
    signal[(score >= 70) & (score <= 84)] = "ACQUISTO"
    signal[(score >= 85) & (score <= 100)] = "ACQUISTO FORTE"
    df["Segnale"] = signal
    return df


def apply_sell_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Regole di vendita (priorità assoluta):
    Se una delle condizioni è vera:
    - Close < SMA200
    - SMA50 < SMA200
    - RSI > 80 e distanza dalla SMA200 > 30%

    Allora:
    Segnale = RIDURRE ESPOSIZIONE
    """
    df = df.copy()

    close = df["Close"]
    sma50 = df["SMA50"]
    sma200 = df["SMA200"]
    rsi = df["RSI"]
    distance_pct = df["DistanceFromSMA200_Pct"]

    sell_cond1 = close < sma200
    sell_cond2 = sma50 < sma200
    sell_cond3 = (rsi > 80) & (distance_pct > 30)

    any_sell = sell_cond1 | sell_cond2 | sell_cond3

    # Reason testuale per motivazione (opzionale ma utile per report).
    reason = np.full(len(df), "", dtype=object)
    reason[sell_cond1] = "Close < SMA200"
    reason[~sell_cond1 & sell_cond2] = "SMA50 < SMA200"
    reason[~(sell_cond1 | sell_cond2) & sell_cond3] = "RSI > 80 e distanza SMA200 > 30%"

    df.loc[any_sell, "Segnale"] = "RIDURRE ESPOSIZIONE"
    df.loc[any_sell, "SellReason"] = reason[any_sell]
    return df


def compute_signals(df_indicators: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline completa:
    - calcola punteggio
    - classifica
    - applica vendita (override)
    """
    df = score_rowwise(df_indicators)
    df = classify_by_score(df)
    df = apply_sell_rules(df)

    # Estensione futura (on-chain) - placeholder
    # Se in futuro aggiungerai colonne on-chain (MVRV, NUPL, Puell Multiple, ecc.),
    # qui puoi implementare un filtro extra "prudente".
    #
    # Esempio di comportamento prudente (solo idea):
    # - se MVRV è in zona storicamente "eccesso", forzare RIDURRE ESPOSIZIONE
    # - se NUPL indica "capitolazione/accumulo" e MVRV è favorevole, permettere BUY
    #
    # Per ora NON alteriamo la logica richiesta dalla specifica.
    df = apply_onchain_filters_placeholder(df)

    return df


def apply_onchain_filters_placeholder(df_with_signals: pd.DataFrame) -> pd.DataFrame:
    """
    Stub per filtri on-chain.

    In futuro:
    - caricherai dati on-chain (probabilmente da provider/API o CSV locale)
    - farai merge su date
    - aggiornerai df_with_signals["Segnale"] in modo conservativo

    Restituisce:
        df_with_signals inalterato (comportamento attuale).
    """
    # TODO: implementare quando disponibili i dati on-chain.
    return df_with_signals


def explain_latest_row(df_with_signals: pd.DataFrame) -> str:
    """
    Produce una motivazione testuale dettagliata per l'ultima riga.
    """
    row = df_with_signals.iloc[-1]

    punteggio = row.get("Punteggio", np.nan)
    segnale = row.get("Segnale", "N/A")

    parts: list[str] = []
    parts.append(f"Segnale finale: {segnale}")
    parts.append(f"Punteggio: {punteggio:.0f}/100")

    # Componenti punteggio (se disponibili)
    parts.append(f"Trend principale (Close > SMA200): {'SI' if row['Close'] > row['SMA200'] else 'NO'} (+25 se SI)")
    parts.append(f"Trend secondario (SMA50 > SMA200): {'SI' if row['SMA50'] > row['SMA200'] else 'NO'} (+25 se SI)")

    rsi = row["RSI"]
    if 40 <= rsi <= 65:
        parts.append(f"RSI: {rsi:.1f} => 40..65 => +15")
    elif 30 <= rsi < 40:
        parts.append(f"RSI: {rsi:.1f} => 30..40 => +10")
    elif rsi > 75:
        parts.append(f"RSI: {rsi:.1f} => >75 => 0 punti")
    elif rsi < 30:
        parts.append(f"RSI: {rsi:.1f} => <30 => 0 punti")
    else:
        parts.append(f"RSI: {rsi:.1f} => nessun range favorevole => 0 punti")

    # Volume
    vol_ok = row["Volume"] > row["VolumeAvg20"]
    parts.append(f"Volume: {'odierno > media20' if vol_ok else 'odierno <= media20'} => {'+15' if vol_ok else '0'}")

    # Distanza
    dist = row["DistanceFromSMA200_Pct"]
    if 0 <= dist <= 20:
        parts.append(f"Distanza SMA200: {dist:.2f}% => 0..20 => +20")
    elif dist > 40:
        parts.append(f"Distanza SMA200: {dist:.2f}% => >40 => 0 punti")
    else:
        parts.append(f"Distanza SMA200: {dist:.2f}% => fuori range favorevole => 0 punti")

    # Sell override
    if segnale == "RIDURRE ESPOSIZIONE":
        reason = row.get("SellReason", "")
        parts.append(f"Override vendita: {reason or 'condizione di rischio attiva'}")

    return "\n".join(parts)

