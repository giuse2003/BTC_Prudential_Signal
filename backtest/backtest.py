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
    Sharpe ratio annualizzato sul calendario crypto (365 giorni).

    risk_free_rate:
    - per semplicità e per coerenza con un'app locale prudente, default 0.
    """
    r = daily_returns.dropna()
    if len(r) < 2:
        return float("nan")

    # Excess returns: per risk_free_rate annuo convertiamo in giornaliero.
    # In pratica qui è 0 di default.
    rf_daily = risk_free_rate / CFG.periods_per_year
    excess = r - rf_daily

    mean_excess = excess.mean()
    std = excess.std(ddof=1)
    if std == 0:
        return float("nan")

    return float(np.sqrt(CFG.periods_per_year) * mean_excess / std)


def _completed_trade_returns(
    effective_exposure: pd.Series,
    daily_strategy_returns: pd.Series,
) -> list[float]:
    """
    Restituisce i rendimenti dei soli trade long completati.

    Un trade inizia quando l'esposizione passa da 0 a un valore positivo e si
    conclude quando torna a 0. Una posizione ancora aperta a fine serie non
    entra nel numero operazioni ne' nel win rate.
    """
    active = effective_exposure.gt(0.0)
    trade_returns: list[float] = []
    start_pos: int | None = None

    for pos, is_active in enumerate(active.to_numpy()):
        if is_active and start_pos is None:
            start_pos = pos
        elif not is_active and start_pos is not None:
            returns = daily_strategy_returns.iloc[start_pos:pos].fillna(0.0)
            trade_returns.append(float((1.0 + returns).prod() - 1.0))
            start_pos = None

    return trade_returns


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
    annualized_return = float(
        (equity_strategy.iloc[-1] / equity_strategy.iloc[0])
        ** (CFG.periods_per_year / n_days)
        - 1.0
    )
    max_dd = _max_drawdown(equity_strategy)

    # Operazioni e win rate
    completed_trade_returns = _completed_trade_returns(
        effective_exposure,
        daily_strategy_returns,
    )
    num_operations = len(completed_trade_returns)
    wins = sum(trade_return > 0.0 for trade_return in completed_trade_returns)
    win_rate = wins / float(num_operations) if num_operations else 0.0

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
    bh_annualized_return = float(
        (equity_bh.iloc[-1] / equity_bh.iloc[0])
        ** (CFG.periods_per_year / n_days)
        - 1.0
    )
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

