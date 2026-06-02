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
    Salva CSV con le colonne richieste dalla specifica.

    Colonne richieste:
    - Data
    - Prezzo
    - SMA50
    - SMA200
    - RSI
    - Punteggio
    - Segnale
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df_out = df.copy()
    df_out = df_out.rename(
        columns={
            "Close": "Prezzo",
        }
    )
    df_out["Data"] = df_out.index.strftime("%Y-%m-%d")

    cols = ["Data", "Prezzo", "SMA50", "SMA200", "RSI", "Punteggio", "Segnale"]
    missing = [c for c in cols if c not in df_out.columns]
    if missing:
        raise ValueError(f"Colonne mancanti per CSV: {missing}")

    df_out[cols].to_csv(out_path, index=False)
    return out_path


def save_text_report(
    df: pd.DataFrame,
    metrics_strategy,
    metrics_bh,
    out_path: str | Path,
    price_eur: float | None = None,
) -> Path:
    """
    Crea il report testuale completo.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    latest = df.iloc[-1]
    day = df.index[-1].strftime("%Y-%m-%d")

    motivazione = explain_latest_row(df, price_eur=price_eur)

    # Informazioni su indicatori (richiesti / utili dal report testuale).
    atr = float(latest.get("ATR", float("nan")))
    high52w = float(latest.get("High52w", float("nan")))
    low52w = float(latest.get("Low52w", float("nan")))

    lines: list[str] = []
    lines.append("BITCOIN ANALYSIS")
    lines.append(f"Data: {day}")
    lines.append("")
    lines.append(f"Prezzo: {float(latest['Close']):.4f} USD")
    lines.append(f"SMA50: {float(latest['SMA50']):.4f}")
    lines.append(f"SMA200: {float(latest['SMA200']):.4f}")
    lines.append(f"RSI: {float(latest['RSI']):.2f}")
    lines.append(f"ATR: {atr:.4f}")
    lines.append(f"Massimo 52w: {high52w:.4f}")
    lines.append(f"Minimo 52w: {low52w:.4f}")
    lines.append("")
    lines.append(f"Punteggio: {float(latest['Punteggio']):.0f}/100")
    lines.append(f"Segnale: {latest['Segnale']}")
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
    sell_label = "VENDI / RIDUCI ESPOSIZIONE"

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

