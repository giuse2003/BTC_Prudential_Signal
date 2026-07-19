"""
App Python prudente per generare segnali BUY/SELL su Bitcoin con approccio
estremamente orientato alla conservazione del capitale.

Pipeline:
1) Scarica dati giornalieri BTC-USD da Yahoo Finance (yfinance)
2) Calcola indicatori tecnici richiesti
3) Calcola punteggio 0..100 e Segnale (ACQUISTA / MANTIENI / VENDI)
4) Calcola il livello di rischio informativo
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
from data.daily_candles import keep_closed_daily_candles
from indicators.technical_indicators import compute_all_indicators
from live.coinbase import fetch_spot_price
from reports.generate import (
    plot_price_and_sma_with_signals,
    save_historical_csv,
    save_chart_data_json,
    save_text_report,
    save_status_json,
)
from strategy.signals import compute_signals
from backtest.backtest import run_backtest
from notifications.telegram import TelegramConfig, send_telegram_message


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
    csv_path_usd = fetch_btc_daily_csv(symbol="BTC-USD", force_download=args.force_download, is_optional=False)
    df_usd = keep_closed_daily_candles(load_daily_csv(csv_path_usd))
    
    csv_path_eur = fetch_btc_daily_csv(symbol="BTC-EUR", force_download=args.force_download, is_optional=True)
    if csv_path_eur is not None:
        try:
            df_eur = keep_closed_daily_candles(load_daily_csv(csv_path_eur))
            df_eur_close = df_eur["Close"].rename("Close_EUR")
            df = df_usd.join(df_eur_close, how="left")
            df["Close_EUR"] = df["Close_EUR"].ffill().bfill()
        except Exception as e:
            print(f"ATTENZIONE: Errore nel caricamento del file BTC-EUR: {e}. Continuo senza dati EUR storici.")
            df = df_usd.copy()
            df["Close_EUR"] = float("nan")
    else:
        df = df_usd.copy()
        df["Close_EUR"] = float("nan")

    # 2) Indicatori
    df_ind = compute_all_indicators(df)

    # 3) Segnali (score + classificazione + override di vendita + livello di rischio)
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

    # Coinbase spot prices
    try:
        spot_eur = fetch_spot_price("BTC-EUR", timeout_s=5).price
    except Exception:
        print("ATTENZIONE: Impossibile recuperare il prezzo spot BTC-EUR live.")
        spot_eur = None

    try:
        spot_usd = fetch_spot_price("BTC-USD", timeout_s=5).price
    except Exception:
        print("ATTENZIONE: Impossibile recuperare il prezzo spot BTC-USD live.")
        spot_usd = None

    report_path = out_reports / "report.txt"
    save_text_report(
        df_signals,
        metrics_strategy=metrics_strategy,
        metrics_bh=metrics_bh,
        out_path=report_path,
        price_eur=spot_eur,
        price_usd=spot_usd,
    )

    # Salva status.json per la dashboard
    status_json_path = out_reports / "status.json"
    save_status_json(df_signals, price_eur=spot_eur, price_usd=spot_usd, out_path=status_json_path)
    chart_data_path = out_reports / "chart-data.json"
    save_chart_data_json(df_signals, out_path=chart_data_path)

    chart_path = out_reports / "price_sma_signals.png"
    plot_price_and_sma_with_signals(df_signals, chart_path)

    latest = df_signals.iloc[-1]
    day = df_signals.index[-1].strftime("%Y-%m-%d")

    # Invia notifica Telegram se avviato manualmente ed esistono credenziali
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if bot_token and chat_id:
        try:
            cfg = TelegramConfig(bot_token=bot_token, chat_id=chat_id)
            send_telegram_message(cfg, "BTC Monitor attivo e funzionante.")
            print("Notifica Telegram inviata con successo (avvio manuale).")
        except Exception as e:
            print(f"ATTENZIONE: Impossibile inviare la notifica Telegram: {e}")

    print("Operazione completata.")
    print("")
    print("Riepilogo ultimo giorno:")
    print(f"- Data: {day}")
    if spot_usd:
        print(f"- Prezzo USD: {spot_usd:,.2f} USD (live da Coinbase)")
    else:
        print(f"- Prezzo USD: {float(latest['Close']):.2f} USD")
    if spot_eur:
        print(f"- Prezzo EUR: {spot_eur:,.2f} EUR (live da Coinbase)")
    elif "Close_EUR" in latest and not pd.isna(latest["Close_EUR"]):
        print(f"- Prezzo EUR: {float(latest['Close_EUR']):.2f} EUR")
    else:
        print("- Prezzo EUR: non disponibile")
    print(f"- Segnale: {latest['Segnale']}")
    print(f"- Livello di rischio: {latest.get('Livello_Rischio', 'MEDIO')}")
    print("")
    print(f"Report: {report_path}")
    print(f"CSV storico: {latest_csv}")
    print(f"Dati grafico: {chart_data_path}")
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

