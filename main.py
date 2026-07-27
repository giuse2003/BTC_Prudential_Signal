"""Esegue la pipeline riproducibile di BTC-USD Signal."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BTC-USD Signal su dati Coinbase daily UTC.")
    parser.add_argument("--force-download", action="store_true", help="Ricostruisce la cache Coinbase")
    parser.add_argument("--initial-capital", type=float, default=1.0)
    parser.add_argument("--open", action="store_true", help="Apre report e grafico su Windows")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parent
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
