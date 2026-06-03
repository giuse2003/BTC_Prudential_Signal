"""
Backtest per la strategia prudente.

Interpretazione prudente di "Segnale" -> esposizione capitale:
- ACQUISTA -> 100%
- MANTIENI -> conserva l'esposizione precedente
- VENDI -> 0%

Nota importante (per evitare bias):
- I segnali sono calcolati usando i dati "di oggi" (Close di oggi).
- Per simulare in modo conservativo, applichiamo l'esposizione calcolata oggi
  ai rendimenti del giorno successivo (shift di 1 giorno).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import CFG


@dataclass(frozen=True)
class BacktestMetrics:
    total_return: float
    annualized_return: float
    max_drawdown: float
    num_operations: int
    win_rate: float
    sharpe_ratio: float


def _max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min())


def _sharpe_ratio(daily_returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Sharpe ratio annualizzato (252 giorni).

    risk_free_rate:
    - per semplicità e per coerenza con un'app locale prudente, default 0.
    """
    r = daily_returns.dropna()
    if len(r) < 2:
        return float("nan")

    # Excess returns: per risk_free_rate annuo convertiamo in giornaliero.
    # In pratica qui è 0 di default.
    rf_daily = risk_free_rate / 252.0
    excess = r - rf_daily

    mean_excess = excess.mean()
    std = excess.std(ddof=1)
    if std == 0:
        return float("nan")

    return float(np.sqrt(252) * mean_excess / std)


def exposure_from_signal(signals: pd.Series, exposure_map: dict[str, float]) -> pd.Series:
    """
    Mappa stringhe di segnale -> esposizione frazione di capitale.
    """
    # default prudente se troviamo segnali non previsti = NaN (MANTIENI)
    default = float("nan")
    return signals.map(lambda s: exposure_map.get(s, default)).astype(float)


def run_backtest(df: pd.DataFrame, initial_capital: float = 1.0) -> tuple[pd.DataFrame, BacktestMetrics, BacktestMetrics]:
    """
    Parametri
    ----------
    df:
        DataFrame con index datetime e colonne:
        - Close
        - Segnale

    Returns
    -------
    (equity_df, metrics_strategy, metrics_bh)
    """
    if "Close" not in df.columns or "Segnale" not in df.columns:
        raise ValueError("df deve contenere 'Close' e 'Segnale'.")

    df = df.sort_index().copy()

    desired_exposure = exposure_from_signal(df["Segnale"], CFG.exposure_map)

    # I NaN in desired_exposure indicano "MANTIENI" -> usiamo ffill() per propagare la posizione
    desired_exposure = desired_exposure.ffill().fillna(0.0)

    # esposizione effettiva per il rendimento di oggi:
    # se segnale(t) è calcolato a chiusura t, lo applichiamo a rendimenti t->t+1,
    # quindi per il rendimento del giorno t useremo desired_exposure(t-1).
    effective_exposure = desired_exposure.shift(1).fillna(0.0)

    btc_returns = df["Close"].pct_change()
    daily_strategy_returns = effective_exposure * btc_returns

    # Equity strategy
    equity_strategy = (1.0 + daily_strategy_returns.fillna(0.0)).cumprod() * float(initial_capital)

    # Buy & Hold:
    # investiamo 100% in BTC al primo Close disponibile.
    equity_bh = (df["Close"] / float(df["Close"].iloc[0])) * float(initial_capital)

    equity_df = pd.DataFrame(
        {
            "EquityStrategy": equity_strategy,
            "EquityBuyHold": equity_bh,
            "DailyReturnStrategy": daily_strategy_returns,
            "DailyReturnBuyHold": btc_returns,
            "EffectiveExposure": effective_exposure,
        },
        index=df.index,
    )

    # Metriche
    n_days = max(len(df) - 1, 1)
    total_return = float(equity_strategy.iloc[-1] / equity_strategy.iloc[0] - 1.0)
    annualized_return = float((equity_strategy.iloc[-1] / equity_strategy.iloc[0]) ** (252.0 / n_days) - 1.0)
    max_dd = _max_drawdown(equity_strategy)

    # Operazioni e win rate
    # "Operazione" = giorno in cui cambia l'esposizione effettiva (BTC fraction detenuta).
    prev_exposure = effective_exposure.shift(1).fillna(effective_exposure.iloc[0])
    change_mask = effective_exposure.ne(prev_exposure)

    # Non contiamo il primo giorno (già impostato a 0 o comunque baseline).
    change_dates = df.index[change_mask].tolist()
    if len(change_dates) > 0:
        change_dates = change_dates[1:]

    num_operations = len(change_dates)

    # Se num_operations=0 => win rate e Sharpe possono essere NaN/0; scegliamo 0 per win_rate.
    win_rate = 0.0
    if num_operations > 0:
        wins = 0
        # Costruiamo segmenti tra date di cambio esposizione.
        # Per ciascuna operazione, guardiamo il rendimento della strategia
        # fino al prossimo cambio (inclusivo del giorno di inizio segmento).
        all_change_dates = [df.index[0]] + df.index[change_mask].tolist()  # include start
        all_change_dates = sorted(set(all_change_dates))

        # Segmenti: da change i a change i+1 - 1 giorno.
        for i, start_date in enumerate(all_change_dates[:-1]):
            end_date = all_change_dates[i + 1]
            # Segment end: giorno prima dell'end_date, se end_date non è il primo.
            # Se start_date == end_date, skip.
            if start_date == end_date:
                continue

            # posizione
            start_pos = df.index.get_loc(start_date)
            end_pos = df.index.get_loc(end_date) - 1
            if end_pos < start_pos:
                continue

            seg_return = float(equity_strategy.iloc[end_pos] / equity_strategy.iloc[start_pos] - 1.0)

            # Segmento conta come "post-operazione" solo se all'istante di inizio
            # l'esposizione è > 0 (quindi non stiamo solo restando fuori dal mercato).
            seg_exposure = float(effective_exposure.iloc[start_pos])
            if seg_exposure > 0 and seg_return > 0:
                wins += 1

        # win_rate basato sugli ultimi cambi che corrispondono a decisioni operative.
        # In pratica stimiamo win sui segmenti "attivi" contati nel ciclo sopra.
        # Per coerenza, il denominatore scelto è num_operations.
        win_rate = wins / float(num_operations)

    sharpe_strategy = _sharpe_ratio(equity_df["DailyReturnStrategy"])

    metrics_strategy = BacktestMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        max_drawdown=max_dd,
        num_operations=num_operations,
        win_rate=win_rate,
        sharpe_ratio=sharpe_strategy,
    )

    # Metriche Buy & Hold (nessuna "operazione" significativa per questa metrica)
    bh_total_return = float(equity_bh.iloc[-1] / equity_bh.iloc[0] - 1.0)
    bh_annualized_return = float((equity_bh.iloc[-1] / equity_bh.iloc[0]) ** (252.0 / n_days) - 1.0)
    bh_max_dd = _max_drawdown(equity_bh)
    bh_sharpe = _sharpe_ratio(equity_df["DailyReturnBuyHold"])

    metrics_bh = BacktestMetrics(
        total_return=bh_total_return,
        annualized_return=bh_annualized_return,
        max_drawdown=bh_max_dd,
        num_operations=0,
        win_rate=0.0,
        sharpe_ratio=bh_sharpe,
    )

    return equity_df, metrics_strategy, metrics_bh

