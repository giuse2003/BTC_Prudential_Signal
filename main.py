"""
App Python prudente per generare segnali BUY/SELL su Bitcoin con approccio
estremamente orientato alla conservazione del capitale.

Pipeline:
1) Scarica dati giornalieri BTC-USD da Yahoo Finance (yfinance)
2) Calcola indicatori tecnici richiesti
3) Calcola punteggio 0..100 e Segnale (EVITARE / ACCUMULO GRADUALE / ACQUISTO / ACQUISTO FORTE)
4) Applica override di rischio: RIDURRE ESPOSIZIONE
5) Backtest 2015..oggi vs Buy & Hold
6) Output:
   - report testuale
   - CSV storico con indicatori + segnali
   - grafico prezzo + SMA50/SMA200 + markers

Esecuzione locale (Windows, Python 3.13):
1. install dipendenze:
   pip install -r requirements.txt
2. avvio:
   python main.py
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from data.fetch_yahoo import fetch_btc_daily_csv, load_daily_csv
from indicators.technical_indicators import compute_all_indicators
from live.coinbase import fetch_spot_price
from reports.generate import plot_price_and_sma_with_signals, save_historical_csv, save_text_report
from strategy.signals import compute_signals
from backtest.backtest import run_backtest


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prudential BTC buy/sell signals (technical + scoring).")
    p.add_argument("--symbol", default="BTC-USD", help="Yahoo Finance symbol (default: BTC-USD)")
    p.add_argument("--force-download", action="store_true", help="Forza download anche se il CSV esiste")
    p.add_argument("--initial-capital", type=float, default=1.0, help="Capitale iniziale (default 1.0)")
    p.add_argument(
        "--open",
        action="store_true",
        help="A fine esecuzione apre automaticamente report e grafico (Windows).",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    project_root = Path(__file__).resolve().parent
    out_reports = project_root / "reports"
    out_data = project_root / "data"

    out_reports.mkdir(parents=True, exist_ok=True)
    out_data.mkdir(parents=True, exist_ok=True)

    # 1) Download / load dati
    csv_path = fetch_btc_daily_csv(symbol=args.symbol, force_download=args.force_download)
    df = load_daily_csv(csv_path)

    # 2) Indicatori
    df_ind = compute_all_indicators(df)

    # 3) Segnali (score + classificazione + override di vendita)
    df_signals = compute_signals(df_ind)

    # 4) Salvataggi dei dataset intermedi (utile per debug e modifiche future)
    df_signals.to_csv(out_data / "indicators_with_signals.csv", index=True)

    # 5) Backtest: strategia proposta vs Buy & Hold
    bt_input = df_signals[["Close", "Segnale"]].copy()
    equity_df, metrics_strategy, metrics_bh = run_backtest(bt_input, initial_capital=args.initial_capital)
    equity_df.to_csv(out_reports / "equity_timeseries.csv", index=True)

    # 6) Output richiesti
    latest_csv = out_reports / "historical_signals.csv"
    save_historical_csv(df_signals, latest_csv)

    try:
        spot_eur = fetch_spot_price("BTC-EUR", timeout_s=5).price
    except Exception:
        spot_eur = None

    report_path = out_reports / "report.txt"
    save_text_report(
        df_signals,
        metrics_strategy=metrics_strategy,
        metrics_bh=metrics_bh,
        out_path=report_path,
        price_eur=spot_eur,
    )

    chart_path = out_reports / "price_sma_signals.png"
    plot_price_and_sma_with_signals(df_signals, chart_path)

    latest = df_signals.iloc[-1]
    day = df_signals.index[-1].strftime("%Y-%m-%d")

    print("Operazione completata.")
    print("")
    print("Riepilogo ultimo giorno:")
    print(f"- Data: {day}")
    if spot_eur:
        print(f"- Prezzo: {spot_eur:,.2f} EUR (live da Coinbase)")
    else:
        print(f"- Prezzo: {float(latest['Close']):.2f} USD")
    print(f"- Segnale: {latest['Segnale']}")
    print("")
    print(f"Report: {report_path}")
    print(f"CSV storico: {latest_csv}")
    print(f"Grafico: {chart_path}")

    if args.open and os.name == "nt":
        # Apri in modo non bloccante con l'app predefinita di Windows.
        try:
            os.startfile(str(report_path))  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            os.startfile(str(chart_path))  # type: ignore[attr-defined]
        except Exception:
            pass


if __name__ == "__main__":
    main()

