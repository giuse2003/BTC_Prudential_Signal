"""Esegue la pipeline riproducibile di BTC-USD Signal."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from data.coinbase import fetch_daily_candles
from pipeline import run_pipeline
from reproducibility import create_frozen_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BTC-USD Signal su dati Coinbase daily UTC.")
    parser.add_argument("--force-download", action="store_true", help="Ricostruisce la cache Coinbase")
    parser.add_argument("--initial-capital", type=float, default=1.0)
    parser.add_argument("--as-of", help="Congela il backtest all'ultima candela YYYY-MM-DD")
    parser.add_argument("--output-dir", type=Path, help="Directory del baseline congelato")
    parser.add_argument("--open", action="store_true", help="Apre report e grafico su Windows")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
    if args.as_of:
        output = args.output_dir or root / "docs" / "runs" / f"baseline-v1-{args.as_of}"
        candles = fetch_daily_candles(
            as_of=args.as_of,
            refresh_all=args.force_download,
        )
        manifest = create_frozen_run(
            candles,
            as_of=args.as_of,
            output_dir=output,
            source_tag=f"baseline-v1-{args.as_of}",
            initial_capital=args.initial_capital,
        )
        print(f"Baseline congelato e riproducibile: {manifest}")
        return

    reports = root / "reports"
    result = run_pipeline(
        output_dir=reports,
        initial_capital=args.initial_capital,
        refresh_all=args.force_download,
    )
    print(f"Esecuzione {result.run_id} completata e validata.")
    print(f"Periodo valutato: {result.evaluation_start} - {result.evaluation_end}")
    print(f"Azione DAILY: {result.daily_action}")
    print(f"Azione LIVE PREVIEW: {result.live_action}")
    print(f"BTC-USD: {result.price_usd:,.2f} USD")
    print(f"BTC-EUR informativo: {result.price_eur:,.2f} EUR")
    print(f"Manifest: {reports / 'manifest.json'}")

    if args.open and os.name == "nt":
        for path in (reports / "report.txt", reports / "price_sma_signals.png"):
            try:
                os.startfile(str(path))  # type: ignore[attr-defined]
            except OSError:
                pass


if __name__ == "__main__":
    main()
