"""Pipeline unica per dati, modello, backtest e pubblicazione."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from backtest.backtest import BacktestMetrics, run_backtest
from config import CFG
from data.coinbase import fetch_daily_candles, fetch_product_snapshot
from indicators.technical_indicators import compute_all_indicators
from reports.generate import (
    plot_price_and_sma_with_signals,
    save_chart_data_json,
    save_historical_csv,
    save_live_status_json,
    save_status_json,
    save_text_report,
)
from reports.publication import (
    new_run_metadata,
    publish_bundle,
    staged_run,
    validate_bundle,
    write_manifest,
)
from strategy.signals import build_live_signal_frame, compute_signals, live_condition_statuses

ARTIFACT_NAMES = [
    "status.json",
    "live-status.json",
    "chart-data.json",
    "historical_signals.csv",
    "equity_timeseries.csv",
    "report.txt",
    "price_sma_signals.png",
]


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    candle_date: str
    daily_action: str
    live_action: str
    live_conditions_key: str
    price_usd: float
    price_eur: float
    volume_24h_btc: float
    buy_statuses: list[bool]
    sell_statuses: list[bool]
    strategy_metrics: BacktestMetrics
    buy_hold_metrics: BacktestMetrics
    evaluation_start: str
    evaluation_end: str


def _metrics_payload(metrics: BacktestMetrics) -> dict:
    return asdict(metrics)


def _evaluation_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = ["SMA200", "SMA50", "RSI", "VolumeAvg20", f"Close_{CFG.momentum_days}d_ago"]
    evaluated = frame.dropna(subset=required).copy()
    if evaluated.empty:
        raise ValueError("Storico insufficiente dopo il warm-up SMA200.")
    return evaluated


def run_pipeline(
    *,
    output_dir: str | Path,
    initial_capital: float = 1.0,
    refresh_all: bool = False,
    now_utc: pd.Timestamp | None = None,
) -> PipelineResult:
    output_dir = Path(output_dir)
    metadata = new_run_metadata()

    candles = fetch_daily_candles(refresh_all=refresh_all, now_utc=now_utc)
    signals_all = compute_signals(compute_all_indicators(candles))
    evaluated = _evaluation_frame(signals_all)

    equity, strategy_metrics, buy_hold_metrics = run_backtest(
        evaluated[["Close", "Segnale"]],
        initial_capital=initial_capital,
    )
    usd_market = fetch_product_snapshot(CFG.product_id)
    eur_market = fetch_product_snapshot(CFG.informational_product_id)
    if usd_market.volume_24h is None:
        raise ValueError("Coinbase non ha restituito il volume 24h BTC-USD.")

    live_frame = build_live_signal_frame(
        candles,
        live_price_usd=usd_market.price,
        live_volume_24h=usd_market.volume_24h,
        live_time_utc=now_utc,
    )
    live_buy, live_sell = live_condition_statuses(live_frame)
    live_latest = live_frame.iloc[-1]
    live_action = str(live_latest["Segnale"])
    conditions_key = (
        "BUY:" + "".join("1" if value else "0" for value in live_buy)
        + "|SELL:" + "".join("1" if value else "0" for value in live_sell)
    )

    period = {
        "coinbase_history_start": candles.index[0].strftime("%Y-%m-%d"),
        "warmup_end": (evaluated.index[0] - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        "evaluation_start": evaluated.index[0].strftime("%Y-%m-%d"),
        "evaluation_end": evaluated.index[-1].strftime("%Y-%m-%d"),
        "calendar_days": int((evaluated.index[-1] - evaluated.index[0]).days + 1),
    }
    metrics = {
        "strategy": _metrics_payload(strategy_metrics),
        "buy_and_hold": _metrics_payload(buy_hold_metrics),
    }

    with staged_run(output_dir) as staging:
        save_status_json(
            evaluated,
            metadata=metadata,
            out_path=staging / "status.json",
        )
        save_live_status_json(
            action=live_action,
            price_usd=usd_market.price,
            price_eur=eur_market.price,
            volume_24h_btc=usd_market.volume_24h,
            buy_statuses=live_buy,
            sell_statuses=live_sell,
            rsi=float(live_latest["RSI"]),
            sma50=float(live_latest["SMA50"]),
            sma200=float(live_latest["SMA200"]),
            atr=float(live_latest["ATR"]),
            risk_level=str(live_latest["Livello_Rischio"]),
            metadata=metadata,
            out_path=staging / "live-status.json",
        )
        save_chart_data_json(evaluated, staging / "chart-data.json", metadata)
        save_historical_csv(evaluated, staging / "historical_signals.csv")
        equity.to_csv(staging / "equity_timeseries.csv", index=True)
        save_text_report(
            evaluated,
            strategy_metrics,
            buy_hold_metrics,
            staging / "report.txt",
            price_eur=eur_market.price,
            price_usd=usd_market.price,
        )
        plot_price_and_sma_with_signals(evaluated, staging / "price_sma_signals.png")
        write_manifest(
            staging,
            metadata,
            period=period,
            metrics=metrics,
            artifact_names=ARTIFACT_NAMES,
        )
        validate_bundle(staging)
        publish_bundle(staging, output_dir, ARTIFACT_NAMES)

    return PipelineResult(
        run_id=metadata["run_id"],
        candle_date=evaluated.index[-1].strftime("%Y-%m-%d"),
        daily_action=str(evaluated.iloc[-1]["Segnale"]),
        live_action=live_action,
        live_conditions_key=conditions_key,
        price_usd=usd_market.price,
        price_eur=eur_market.price,
        volume_24h_btc=usd_market.volume_24h,
        buy_statuses=live_buy,
        sell_statuses=live_sell,
        strategy_metrics=strategy_metrics,
        buy_hold_metrics=buy_hold_metrics,
        evaluation_start=period["evaluation_start"],
        evaluation_end=period["evaluation_end"],
    )
