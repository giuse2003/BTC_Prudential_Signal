"""
Generazione report:
- report testuale
- CSV storico con indicatori e segnali
- grafico (prezzo + SMA50/SMA200 + markers buy/sell)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from config import CFG
from strategy.signals import explain_latest_row


def save_historical_csv(df: pd.DataFrame, out_path: str | Path) -> Path:
    """
    Salva CSV con le colonne richieste per la Versione 1.0.

    Colonne esportate:
    - Data
    - Close (BTC-USD Close)
    - BTC-USD
    - BTC-EUR (Close EUR)
    - SMA50
    - SMA200
    - RSI
    - ATR
    - Volume
    - Segnale
    - Livello_Rischio
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df_out = df.copy()
    df_out["Data"] = df_out.index.strftime("%Y-%m-%d")
    df_out["BTC-USD"] = df_out["Close"]
    
    if "Close_EUR" in df_out.columns:
        df_out["BTC-EUR"] = df_out["Close_EUR"]
    else:
        df_out["BTC-EUR"] = float("nan")

    cols = [
        "Data",
        "Close",
        "BTC-USD",
        "BTC-EUR",
        "SMA50",
        "SMA200",
        "RSI",
        "ATR",
        "Volume",
        "Segnale",
        "Livello_Rischio",
    ]
    
    # In caso di colonne mancanti per vecchi dataset o altro, creale come NaN
    for c in cols:
        if c not in df_out.columns:
            df_out[c] = float("nan")

    df_out[cols].to_csv(out_path, index=False)
    return out_path


def save_chart_data_json(df: pd.DataFrame, out_path: str | Path) -> Path:
    """
    Salva la serie storica compatta usata dalla dashboard e dal comando LIVE.
    """
    import json

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for date, row in df.sort_index().iterrows():
        rows.append(
            {
                "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
                "close": _json_float(row.get("Close")),
                "sma50": _json_float(row.get("SMA50")),
                "sma200": _json_float(row.get("SMA200")),
                "rsi": _json_float(row.get("RSI")),
                "volume": _json_float(row.get("Volume")),
                "volume_avg20": _json_float(row.get("VolumeAvg20")),
                "signal": str(row.get("Segnale", "MANTIENI")),
            }
        )

    out_path.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
    return out_path


def save_live_status_json(
    *,
    signal: str,
    price_usd: float,
    price_eur: float | None,
    volume_24h_usd: float,
    buy_statuses: list[bool],
    sell_statuses: list[bool],
    out_path: str | Path,
) -> Path:
    """
    Salva il segnale LIVE usato da Telegram su richiesta.
    """
    import json
    from datetime import datetime, timezone

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    buy_labels = [
        "prezzo live sopra SMA200 live",
        "SMA50 live sopra SMA200 live",
        "RSI live uguale o maggiore di 40",
        "prezzo live sopra quello di 7 giorni prima",
        "volume 24h live sopra media 20 giorni",
    ]
    sell_labels = ["prezzo live sotto SMA50 live per 2 giorni consecutivi"]
    payload = {
        "signal": signal,
        "price_usd": float(price_usd),
        "price_eur": _json_float(price_eur),
        "volume_24h_usd": float(volume_24h_usd),
        "last_update": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status": "Attivo",
        "condition_groups": {
            "buy": [
                {"label": label, "passed": bool(passed)}
                for label, passed in zip(buy_labels, buy_statuses)
            ],
            "sell": [
                {"label": label, "passed": bool(passed)}
                for label, passed in zip(sell_labels, sell_statuses)
            ],
        },
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def _json_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def save_text_report(
    df: pd.DataFrame,
    metrics_strategy,
    metrics_bh,
    out_path: str | Path,
    price_eur: float | None = None,
    price_usd: float | None = None,
) -> Path:
    """
    Crea il report testuale completo.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    latest = df.iloc[-1]
    day = df.index[-1].strftime("%Y-%m-%d")

    motivazione = explain_latest_row(df, price_eur=price_eur, price_usd=price_usd)

    # Informazioni su indicatori (richiesti / utili dal report testuale).
    atr = float(latest.get("ATR", float("nan")))
    high52w = float(latest.get("High52w", float("nan")))
    low52w = float(latest.get("Low52w", float("nan")))
    rischio = latest.get("Livello_Rischio", "MEDIO")

    lines: list[str] = []
    lines.append("BITCOIN ANALYSIS")
    lines.append(f"Data: {day}")
    lines.append("")
    lines.append(f"Prezzo USD: {float(latest['Close']):.4f} USD")
    if price_eur:
        lines.append(f"Prezzo EUR: {price_eur:.2f} EUR")
    elif "Close_EUR" in latest and not pd.isna(latest["Close_EUR"]):
        lines.append(f"Prezzo EUR: {float(latest['Close_EUR']):.2f} EUR")
    else:
        lines.append("Prezzo EUR: non disponibile")
        
    lines.append(f"SMA50: {float(latest['SMA50']):.4f}")
    lines.append(f"SMA200: {float(latest['SMA200']):.4f}")
    lines.append(f"RSI: {float(latest['RSI']):.2f}")
    lines.append(f"ATR: {atr:.4f}")
    lines.append(f"Massimo 52w: {high52w:.4f}")
    lines.append(f"Minimo 52w: {low52w:.4f}")
    lines.append("")
    lines.append(f"Punteggio: {float(latest['Punteggio']):.0f}/100")
    lines.append(f"Segnale: {latest['Segnale']}")
    lines.append(f"Livello di rischio: {rischio}")
    lines.append("")
    lines.append("Motivazione dettagliata:")
    lines.append(motivazione)
    lines.append("")
    lines.append("BACKTEST (dal 2015 ad oggi)")
    lines.append("")

    def fmt_pct(x: float) -> str:
        if x != x:
            return "n/a"
        return f"{x*100:.2f}%"

    lines.append("Strategia proposta (prudente)")
    lines.append(f"- Rendimento totale: {fmt_pct(metrics_strategy.total_return)}")
    lines.append(f"- Rendimento annualizzato: {fmt_pct(metrics_strategy.annualized_return)}")
    lines.append(f"- Drawdown massimo: {fmt_pct(metrics_strategy.max_drawdown)}")
    lines.append(f"- Numero operazioni: {metrics_strategy.num_operations}")
    lines.append(f"- % operazioni vincenti: {metrics_strategy.win_rate*100:.1f}%")
    lines.append(f"- Sharpe Ratio: {metrics_strategy.sharpe_ratio:.3f}")
    lines.append("")

    lines.append("Buy & Hold")
    lines.append(f"- Rendimento totale: {fmt_pct(metrics_bh.total_return)}")
    lines.append(f"- Rendimento annualizzato: {fmt_pct(metrics_bh.annualized_return)}")
    lines.append(f"- Drawdown massimo: {fmt_pct(metrics_bh.max_drawdown)}")
    # buy&hold non ha "operazioni"
    lines.append(f"- Sharpe Ratio: {metrics_bh.sharpe_ratio:.3f}")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def plot_price_and_sma_with_signals(df: pd.DataFrame, out_path: str | Path) -> Path:
    """
    Grafico:
    - prezzo
    - SMA50 e SMA200
    - markers:
      verde = segnale acquisto
      rosso = segnale vendita (RIDURRE ESPOSIZIONE)
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = df.copy().sort_index()

    fig, ax = plt.subplots(figsize=(12, 7))

    ax.plot(df.index, df["Close"], color="white", linewidth=1.2, alpha=0.9, label="Prezzo (BTC-USD)")
    ax.plot(df.index, df["SMA50"], color="#60a5fa", linewidth=1.0, label=f"SMA{CFG.sma_fast}")
    ax.plot(df.index, df["SMA200"], color="#a78bfa", linewidth=1.0, label=f"SMA{CFG.sma_slow}")

    buy_labels = {"ACQUISTA"}
    sell_label = "VENDI"

    buy_df = df[df["Segnale"].isin(buy_labels)]
    sell_df = df[df["Segnale"] == sell_label]

    ax.scatter(buy_df.index, buy_df["Close"], color="green", s=18, alpha=0.8, label="Acquisto")
    ax.scatter(sell_df.index, sell_df["Close"], color="red", s=18, alpha=0.8, label="Ridurre esposizione")

    ax.set_title("BTC prezzo + SMA50/SMA200 + segnali prudenziali", fontsize=13)
    ax.set_xlabel("Data")
    ax.set_ylabel("USD")

    # Miglior leggibilità date: non troppo fitte
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    ax.grid(True, alpha=0.15)
    ax.legend(loc="upper left")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def save_status_json(
    df: pd.DataFrame,
    price_eur: float | None,
    price_usd: float | None,
    out_path: str | Path,
) -> None:
    """
    Salva lo stato corrente in formato JSON per la dashboard.
    """
    import json
    from datetime import datetime
    import numpy as np

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    latest = df.iloc[-1]
    
    # Prezzi (con robustezza se mancano)
    usd_val = price_usd if price_usd is not None else float(latest["Close"])
    
    eur_val = price_eur
    if eur_val is None:
        eur_val = latest.get("Close_EUR")
        if pd.isna(eur_val):
            eur_val = None
            
    # Gestione NaN per il JSON (non supportato nativamente)
    if eur_val is not None and (np.isnan(eur_val) or eur_val != eur_val):
        eur_val = None
    if usd_val is not None and (np.isnan(usd_val) or usd_val != usd_val):
        usd_val = None

    momentum_col = f"Close_{CFG.momentum_days}d_ago"
    prev = df.iloc[-2] if len(df) >= 2 else None
    sell_below_sma50_2d = bool(
        latest["Close"] < latest["SMA50"]
        and prev is not None
        and prev["Close"] < prev["SMA50"]
    )
    condition_groups = {
        "buy": [
            {
                "label": "prezzo sopra SMA200",
                "passed": bool(latest["Close"] > latest["SMA200"]),
            },
            {
                "label": "SMA50 sopra SMA200",
                "passed": bool(latest["SMA50"] > latest["SMA200"]),
            },
            {
                "label": "RSI uguale o maggiore di 40",
                "passed": bool(latest["RSI"] >= 40),
            },
            {
                "label": f"prezzo sopra quello di {CFG.momentum_days} giorni prima",
                "passed": bool(latest["Close"] > latest[momentum_col]),
            },
            {
                "label": "volume sopra media 20 giorni",
                "passed": bool(latest["Volume"] > latest["VolumeAvg20"]),
            },
        ],
        "sell": [
            {
                "label": "prezzo sotto SMA50 per 2 giorni consecutivi",
                "passed": sell_below_sma50_2d,
            },
        ],
    }

    status_data = {
        "price_usd": usd_val,
        "price_eur": eur_val,
        "signal": str(latest["Segnale"]),
        "risk_level": str(latest.get("Livello_Rischio", "MEDIO")),
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Attivo",
        "rsi": float(latest.get("RSI")) if not pd.isna(latest.get("RSI")) else None,
        "sma50": float(latest.get("SMA50")) if not pd.isna(latest.get("SMA50")) else None,
        "sma200": float(latest.get("SMA200")) if not pd.isna(latest.get("SMA200")) else None,
        "atr": float(latest.get("ATR")) if not pd.isna(latest.get("ATR")) else None,
        "volume": float(latest.get("Volume")) if not pd.isna(latest.get("Volume")) else None,
        "volume_avg20": float(latest.get("VolumeAvg20")) if not pd.isna(latest.get("VolumeAvg20")) else None,
        "close_7d_ago": float(latest.get(momentum_col)) if not pd.isna(latest.get(momentum_col)) else None,
        "close_last_candle": float(latest.get("Close")) if not pd.isna(latest.get("Close")) else None,
        "previous_close": float(prev.get("Close")) if prev is not None and not pd.isna(prev.get("Close")) else None,
        "previous_sma50": float(prev.get("SMA50")) if prev is not None and not pd.isna(prev.get("SMA50")) else None,
        "below_sma50_2d": sell_below_sma50_2d,
        "condition_groups": condition_groups,
    }
    
    out_path.write_text(json.dumps(status_data, indent=2), encoding="utf-8")


