from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backtest.backtest import run_backtest
from config import CFG


OUT_DIR = ROOT / "outputs" / "sell_rule_experiments"


@dataclass(frozen=True)
class Variant:
    name: str
    description: str


VARIANTS = [
    Variant("baseline_sma50_2d", "Regola attuale: Close sotto SMA50 per 2 giorni consecutivi"),
    Variant("sma50_1d", "Vende alla prima chiusura sotto SMA50"),
    Variant("sma50_3d", "Vende dopo 3 chiusure consecutive sotto SMA50"),
    Variant("sma50_2d_or_rsi40", "Regola attuale piu uscita se Close sotto SMA50 e RSI < 40"),
    Variant("sma50_2d_or_rsi50", "Regola attuale piu uscita se Close sotto SMA50 e RSI < 50"),
    Variant("sma50_2d_or_sma60_2d", "Regola attuale oppure Close sotto SMA60 per 2 giorni"),
    Variant("sma50_2d_or_sma70_2d", "Regola attuale oppure Close sotto SMA70 per 2 giorni"),
    Variant("sma50_2d_or_sma80_2d", "Regola attuale oppure Close sotto SMA80 per 2 giorni"),
    Variant("sma50_2d_or_sma90_2d", "Regola attuale oppure Close sotto SMA90 per 2 giorni"),
    Variant("sma50_1d_or_7d_momentum", "Vende sotto SMA50 1 giorno oppure se il rendimento a 7 giorni <= -10%"),
    Variant("sma50_2d_or_7d_momentum", "Regola attuale piu uscita crash: rendimento a 7 giorni <= -10%"),
    Variant("sma50_1d_or_sma200", "Vende sotto SMA50 1 giorno oppure sotto SMA200"),
    Variant("sma50_2d_or_sma200", "Regola attuale oppure Close sotto SMA200"),
    Variant("trend_break_combo", "Vende sotto SMA50 1 giorno, oppure sotto SMA200 con RSI < 45"),
    Variant("atr_defensive", "Vende sotto SMA50 1 giorno oppure sotto SMA50 - 1 ATR"),
    Variant("rolling_high_stop_15", "Vende se scende oltre -15% dal massimo degli ultimi 30 giorni"),
    Variant("hybrid_defensive", "SMA50 1 giorno, crash 7 giorni <= -10%, oppure sotto SMA200 con RSI < 45"),
]


PERIODS = {
    "full": ("2015-01-01", None),
    "2017_bull": ("2017-01-01", "2017-12-31"),
    "2018_bear": ("2018-01-01", "2018-12-31"),
    "2021_top": ("2021-01-01", "2021-12-31"),
    "2022_bear": ("2022-01-01", "2022-12-31"),
    "2024_2026_recent": ("2024-01-01", None),
    "2025_2026_recent": ("2025-01-01", None),
}


def buy_condition(df: pd.DataFrame) -> pd.Series:
    days = CFG.momentum_days
    return (
        (df["Close"] > df["SMA200"])
        & (df["SMA50"] > df["SMA200"])
        & (df["RSI"] >= 40)
        & (df["Close"] > df[f"Close_{days}d_ago"])
        & (df["Volume"] > df["VolumeAvg20"])
    )


def sell_condition(df: pd.DataFrame, variant_name: str) -> pd.Series:
    close = df["Close"]
    sma50 = df["SMA50"]
    sma200 = df["SMA200"]
    rsi = df["RSI"]
    atr = df["ATR"]
    below_sma50 = close < sma50
    below_sma50_2d = below_sma50 & below_sma50.shift(1).fillna(False)
    below_sma50_3d = below_sma50_2d & below_sma50.shift(2).fillna(False)
    momentum_7d = close / df[f"Close_{CFG.momentum_days}d_ago"] - 1.0
    crash_7d = momentum_7d <= -0.10
    below_sma200 = close < sma200
    under_sma200_weak_rsi = below_sma200 & (rsi < 45)
    atr_break = close < (sma50 - atr)
    rolling_high_30 = close.rolling(window=30, min_periods=30).max()
    rolling_stop_15 = close <= rolling_high_30 * 0.85
    sma60 = close.rolling(window=60, min_periods=60).mean()
    sma70 = close.rolling(window=70, min_periods=70).mean()
    sma80 = close.rolling(window=80, min_periods=80).mean()
    sma90 = close.rolling(window=90, min_periods=90).mean()

    if variant_name == "baseline_sma50_2d":
        return below_sma50_2d
    if variant_name == "sma50_1d":
        return below_sma50
    if variant_name == "sma50_3d":
        return below_sma50_3d
    if variant_name == "sma50_2d_or_rsi40":
        return below_sma50_2d | (below_sma50 & (rsi < 40))
    if variant_name == "sma50_2d_or_rsi50":
        return below_sma50_2d | (below_sma50 & (rsi < 50))
    if variant_name == "sma50_2d_or_sma60_2d":
        below_sma60 = close < sma60
        return below_sma50_2d | (below_sma60 & below_sma60.shift(1).fillna(False))
    if variant_name == "sma50_2d_or_sma70_2d":
        below_sma70 = close < sma70
        return below_sma50_2d | (below_sma70 & below_sma70.shift(1).fillna(False))
    if variant_name == "sma50_2d_or_sma80_2d":
        below_sma80 = close < sma80
        return below_sma50_2d | (below_sma80 & below_sma80.shift(1).fillna(False))
    if variant_name == "sma50_2d_or_sma90_2d":
        below_sma90 = close < sma90
        return below_sma50_2d | (below_sma90 & below_sma90.shift(1).fillna(False))
    if variant_name == "sma50_1d_or_7d_momentum":
        return below_sma50 | crash_7d
    if variant_name == "sma50_2d_or_7d_momentum":
        return below_sma50_2d | crash_7d
    if variant_name == "sma50_1d_or_sma200":
        return below_sma50 | below_sma200
    if variant_name == "sma50_2d_or_sma200":
        return below_sma50_2d | below_sma200
    if variant_name == "trend_break_combo":
        return below_sma50 | under_sma200_weak_rsi
    if variant_name == "atr_defensive":
        return below_sma50 | atr_break
    if variant_name == "rolling_high_stop_15":
        return rolling_stop_15
    if variant_name == "hybrid_defensive":
        return below_sma50 | crash_7d | under_sma200_weak_rsi
    raise ValueError(f"Variant sconosciuta: {variant_name}")


def signals_for_variant(df: pd.DataFrame, variant_name: str) -> pd.DataFrame:
    out = df.copy()
    signals = pd.Series("MANTIENI", index=out.index, dtype=object)
    signals.loc[buy_condition(out)] = "ACQUISTA"
    signals.loc[sell_condition(out, variant_name)] = "VENDI"
    out["Segnale"] = signals
    return out


def metric_row(variant: Variant, period_name: str, start: str, end: str | None, df_variant: pd.DataFrame) -> dict:
    period_df = df_variant.loc[start:end, ["Close", "Segnale"]].copy()
    if period_df.empty:
        raise ValueError(f"Periodo vuoto: {period_name}")

    _, strategy, buy_hold = run_backtest(period_df)
    return {
        "variant": variant.name,
        "description": variant.description,
        "period": period_name,
        "start": period_df.index.min().strftime("%Y-%m-%d"),
        "end": period_df.index.max().strftime("%Y-%m-%d"),
        "strategy_total_return": strategy.total_return,
        "strategy_annualized_return": strategy.annualized_return,
        "strategy_max_drawdown": strategy.max_drawdown,
        "strategy_sharpe": strategy.sharpe_ratio,
        "strategy_operations": strategy.num_operations,
        "strategy_win_rate": strategy.win_rate,
        "buy_hold_total_return": buy_hold.total_return,
        "buy_hold_max_drawdown": buy_hold.max_drawdown,
        "delta_total_return": strategy.total_return - buy_hold.total_return,
        "drawdown_improvement": strategy.max_drawdown - buy_hold.max_drawdown,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ROOT / "data" / "indicators_with_signals.csv", parse_dates=["Date"])
    df = df.set_index("Date").sort_index()

    rows: list[dict] = []
    signal_counts: list[dict] = []
    for variant in VARIANTS:
        df_variant = signals_for_variant(df, variant.name)
        full_equity, _, _ = run_backtest(df_variant[["Close", "Segnale"]])
        counts = df_variant["Segnale"].value_counts().to_dict()
        exposure_days = full_equity["EffectiveExposure"].value_counts().to_dict()
        signal_counts.append(
            {
                "variant": variant.name,
                "description": variant.description,
                "buy_days": int(counts.get("ACQUISTA", 0)),
                "hold_days": int(counts.get("MANTIENI", 0)),
                "sell_days": int(counts.get("VENDI", 0)),
                "exposed_days": int(exposure_days.get(1.0, 0)),
                "cash_days": int(exposure_days.get(0.0, 0)),
            }
        )
        for period_name, (start, end) in PERIODS.items():
            rows.append(metric_row(variant, period_name, start, end, df_variant))

    results = pd.DataFrame(rows)
    counts = pd.DataFrame(signal_counts)

    results.to_csv(OUT_DIR / "sell_rule_metrics.csv", index=False)
    counts.to_csv(OUT_DIR / "sell_rule_signal_counts.csv", index=False)

    full = results[results["period"] == "full"].copy()
    full["score"] = (
        full["strategy_total_return"].rank(ascending=False)
        + full["strategy_max_drawdown"].rank(ascending=False)
        + full["strategy_sharpe"].rank(ascending=False)
    )
    full = full.sort_values(
        ["strategy_max_drawdown", "strategy_total_return", "strategy_sharpe"],
        ascending=[False, False, False],
    )

    cols = [
        "variant",
        "strategy_total_return",
        "strategy_annualized_return",
        "strategy_max_drawdown",
        "strategy_sharpe",
        "strategy_operations",
        "strategy_win_rate",
        "delta_total_return",
    ]
    print("\nFULL PERIOD - ordinate per max drawdown migliore")
    print(full[cols].to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    print("\nPERIODI CRITICI - max drawdown strategia")
    pivot = results.pivot(index="variant", columns="period", values="strategy_max_drawdown")
    print(pivot[["2017_bull", "2018_bear", "2022_bear", "2024_2026_recent"]].to_string(float_format=lambda x: f"{x:,.4f}"))

    print(f"\nFile scritti in: {OUT_DIR}")


if __name__ == "__main__":
    main()
