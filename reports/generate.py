"""Generazione degli artefatti coerenti di BTC-USD Signal."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from config import CFG
from strategy.signals import explain_latest_row, live_condition_statuses


def _json_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _condition_groups(buy_statuses: list[bool], sell_statuses: list[bool], live: bool) -> dict:
    qualifier = " live" if live else ""
    buy_labels = [
        f"prezzo{qualifier} sopra SMA200",
        f"RSI{qualifier} uguale o maggiore di 40",
        f"prezzo{qualifier} sopra quello di 7 giorni prima",
        f"volume BTC-USD{qualifier} sopra media 20 giorni",
    ]
    sell_labels = [f"prezzo{qualifier} sotto SMA50 per 2 giorni consecutivi"]
    return {
        "buy": [
            {"label": label, "passed": bool(passed)}
            for label, passed in zip(buy_labels, buy_statuses)
        ],
        "sell": [
            {"label": label, "passed": bool(passed)}
            for label, passed in zip(sell_labels, sell_statuses)
        ],
    }


def save_historical_csv(df: pd.DataFrame, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    output = df.copy()
    output["Data"] = output.index.strftime("%Y-%m-%d")
    output["BTC-USD"] = output["Close"]
    output["Azione"] = output["Segnale"]
    columns = [
        "Data", "Open", "High", "Low", "Close", "BTC-USD", "SMA50", "SMA200",
        "RSI", "ATR", "Volume", "VolumeAvg20", "Azione", "Livello_Rischio",
    ]
    output[columns].to_csv(out_path, index=False)
    return out_path


def save_chart_data_json(
    df: pd.DataFrame,
    out_path: str | Path,
    metadata: dict,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
            "open": _json_float(row.get("Open")),
            "high": _json_float(row.get("High")),
            "low": _json_float(row.get("Low")),
            "close": _json_float(row.get("Close")),
            "sma50": _json_float(row.get("SMA50")),
            "sma200": _json_float(row.get("SMA200")),
            "rsi": _json_float(row.get("RSI")),
            "volume": _json_float(row.get("Volume")),
            "volume_avg20": _json_float(row.get("VolumeAvg20")),
            "action": str(row.get("Segnale", "MANTIENI STATO ATTUALE")),
        }
        for date, row in df.sort_index().iterrows()
    ]
    out_path.write_text(
        json.dumps({**metadata, "mode": "DAILY", "rows": rows}, separators=(",", ":")),
        encoding="utf-8",
    )
    return out_path


def save_live_status_json(
    *,
    action: str,
    price_usd: float,
    price_eur: float | None,
    volume_24h_btc: float,
    buy_statuses: list[bool],
    sell_statuses: list[bool],
    rsi: float | None,
    sma50: float | None,
    sma200: float | None,
    atr: float | None,
    risk_level: str,
    metadata: dict,
    out_path: str | Path,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **metadata,
        "mode": "LIVE PREVIEW",
        "action": action,
        "price_usd": float(price_usd),
        "price_eur": _json_float(price_eur),
        "volume_24h_btc": float(volume_24h_btc),
        "status": "Attivo",
        "rsi": _json_float(rsi),
        "sma50": _json_float(sma50),
        "sma200": _json_float(sma200),
        "atr": _json_float(atr),
        "risk_level": risk_level,
        "condition_groups": _condition_groups(buy_statuses, sell_statuses, live=True),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def save_status_json(
    df: pd.DataFrame,
    *,
    metadata: dict,
    out_path: str | Path,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) >= 2 else None
    buy_statuses, sell_statuses = live_condition_statuses(df)
    payload = {
        **metadata,
        "mode": "DAILY",
        "candle_date": df.index[-1].strftime("%Y-%m-%d"),
        "action": str(latest["Segnale"]),
        "price_usd": _json_float(latest["Close"]),
        "price_eur": None,
        "status": "Attivo",
        "risk_level": str(latest.get("Livello_Rischio", "MEDIO")),
        "rsi": _json_float(latest.get("RSI")),
        "sma50": _json_float(latest.get("SMA50")),
        "sma200": _json_float(latest.get("SMA200")),
        "atr": _json_float(latest.get("ATR")),
        "volume_btc": _json_float(latest.get("Volume")),
        "volume_avg20_btc": _json_float(latest.get("VolumeAvg20")),
        "previous_close": _json_float(previous.get("Close") if previous is not None else None),
        "previous_sma50": _json_float(previous.get("SMA50") if previous is not None else None),
        "condition_groups": _condition_groups(buy_statuses, sell_statuses, live=False),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def save_text_report(
    df: pd.DataFrame,
    metrics_strategy,
    metrics_bh,
    out_path: str | Path,
    *,
    price_eur: float | None = None,
    price_usd: float | None = None,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    latest = df.iloc[-1]

    def pct(value: float) -> str:
        return "n/a" if pd.isna(value) else f"{value * 100:.2f}%"

    lines = [
        CFG.model_name.upper(),
        f"Candela DAILY: {df.index[-1].strftime('%Y-%m-%d')} UTC",
        f"Fonte: {CFG.data_source} - {CFG.product_id}",
        "",
        f"Azione: {latest['Segnale']}",
        f"Rischio informativo: {latest.get('Livello_Rischio', 'MEDIO')}",
        f"Close BTC-USD: {float(latest['Close']):.2f} USD",
        f"Spot BTC-USD: {price_usd:.2f} USD" if price_usd is not None else "Spot BTC-USD: non disponibile",
        f"Spot BTC-EUR: {price_eur:.2f} EUR" if price_eur is not None else "Spot BTC-EUR: non disponibile",
        f"SMA50: {float(latest['SMA50']):.2f}",
        f"SMA200: {float(latest['SMA200']):.2f}",
        f"RSI14: {float(latest['RSI']):.2f}",
        f"ATR14: {float(latest['ATR']):.2f}",
        "",
        explain_latest_row(df, price_eur=price_eur, price_usd=price_usd),
        "",
        f"BACKTEST {df.index[0].strftime('%Y-%m-%d')} - {df.index[-1].strftime('%Y-%m-%d')}",
        "Esecuzione: azione a chiusura t applicata al rendimento t+1",
        "Costi e slippage: non inclusi",
        "",
        CFG.model_name,
        f"- Rendimento totale: {pct(metrics_strategy.total_return)}",
        f"- Rendimento annualizzato: {pct(metrics_strategy.annualized_return)}",
        f"- Drawdown massimo: {pct(metrics_strategy.max_drawdown)}",
        f"- Operazioni completate: {metrics_strategy.num_operations}",
        f"- Operazioni vincenti: {metrics_strategy.win_rate * 100:.1f}%",
        f"- Sharpe Ratio: {metrics_strategy.sharpe_ratio:.3f}",
        "",
        "Buy & Hold BTC-USD",
        f"- Rendimento totale: {pct(metrics_bh.total_return)}",
        f"- Rendimento annualizzato: {pct(metrics_bh.annualized_return)}",
        f"- Drawdown massimo: {pct(metrics_bh.max_drawdown)}",
        f"- Sharpe Ratio: {metrics_bh.sharpe_ratio:.3f}",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def plot_price_and_sma_with_signals(df: pd.DataFrame, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame = df.sort_index()
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.plot(frame.index, frame["Close"], color="white", linewidth=1.2, label="BTC-USD")
    ax.plot(frame.index, frame["SMA50"], color="#38bdf8", linewidth=1.0, label="SMA50")
    ax.plot(frame.index, frame["SMA200"], color="#f59e0b", linewidth=1.0, label="SMA200")
    buys = frame[frame["Segnale"] == "ACQUISTA"]
    sells = frame[frame["Segnale"] == "VENDI"]
    ax.scatter(buys.index, buys["Close"], color="#22c55e", s=18, alpha=0.8, label="ACQUISTA")
    ax.scatter(sells.index, sells["Close"], color="#ef4444", s=18, alpha=0.8, label="VENDI")
    ax.set_title("BTC-USD Signal - DAILY Coinbase")
    ax.set_xlabel("Data UTC")
    ax.set_ylabel("USD")
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(True, alpha=0.15)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
