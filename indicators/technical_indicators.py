"""
Calcolo indicatori tecnici richiesti dalla specifica.

Indicatori:
- SMA50
- SMA200
- RSI(14)
- Volume medio 20 giorni
- ATR(14)
- Massimo e minimo ultimi 52 settimane (365 giorni per il mercato crypto)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import CFG


def add_sma(df: pd.DataFrame, window: int, col_name: str) -> pd.DataFrame:
    """
    Aggiunge una Simple Moving Average (media mobile semplice).
    """
    df = df.copy()
    df[col_name] = df["Close"].rolling(window=window, min_periods=window).mean()
    return df


def add_rsi_14(df: pd.DataFrame, period: int = CFG.rsi_period) -> pd.DataFrame:
    """
    RSI (Relative Strength Index) standard Wilder-like.

    Formule (approccio pratico con ewm):
    - RSI = 100 - (100 / (1 + RS))
    - RS = avg_gain / avg_loss
    """
    df = df.copy()
    delta = df["Close"].diff()

    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    # avg gain/loss "Wilder": ewm con alpha=1/period, adjust=False
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))
    df["RSI"] = rsi
    return df


def add_atr_14(df: pd.DataFrame, period: int = CFG.atr_period) -> pd.DataFrame:
    """
    ATR (Average True Range) standard.

    True Range (TR):
    - max(High - Low, |High - prev_close|, |Low - prev_close|)

    ATR: media Wilder (implementata con ewm(alpha=1/period)).
    """
    df = df.copy()
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # ATR Wilder-like via ewm
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    df["ATR"] = atr
    return df


def add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggiunge volume medio a 20 giorni.
    """
    df = df.copy()
    df["VolumeAvg20"] = df["Volume"].rolling(window=CFG.vol_avg_period, min_periods=CFG.vol_avg_period).mean()
    return df


def add_52w_high_low(df: pd.DataFrame) -> pd.DataFrame:
    """
    Massimo/minimo ultimi 52 settimane (365 giorni di calendario).
    """
    df = df.copy()
    w = CFG.weeks_52_days
    df["High52w"] = df["High"].rolling(window=w, min_periods=w).max()
    df["Low52w"] = df["Low"].rolling(window=w, min_periods=w).min()
    return df


def add_price_momentum(df: pd.DataFrame) -> pd.DataFrame:
    """
    Momentum del prezzo rispetto a N giorni fa.
    """
    df = df.copy()
    days = CFG.momentum_days
    df[f"Close_{days}d_ago"] = df["Close"].shift(days)
    return df


def compute_all_indicators(df_ohlc: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola tutti gli indicatori richiesti e li inserisce in un DataFrame.
    """
    df = df_ohlc.copy()

    df = add_sma(df, CFG.sma_fast, "SMA50")
    df = add_sma(df, CFG.sma_slow, "SMA200")
    df = add_rsi_14(df, CFG.rsi_period)
    df = add_volume_features(df)
    df = add_atr_14(df, CFG.atr_period)
    df = add_52w_high_low(df)
    df = add_price_momentum(df)

    return df

