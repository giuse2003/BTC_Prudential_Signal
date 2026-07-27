"""Esegue l'esperimento isolato sui candidati del modello."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from data.coinbase import fetch_daily_candles
from experiments.candidate_evaluation import AS_OF, create_experiment_run


def _read_candles(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["Date"], index_col="Date")


def main() -> None:
    parser = argparse.ArgumentParser(description="Valuta V1-S1 e V1-B1 senza promuoverli.")
    parser.add_argument("--as-of", default=AS_OF)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/experiments/model-candidates-v1-2026-07-26"),
    )
    parser.add_argument("--eth-input", type=Path)
    parser.add_argument("--refresh-eth", action="store_true")
    args = parser.parse_args()
    if args.as_of != AS_OF:
        raise ValueError(f"Il protocollo registrato richiede --as-of {AS_OF}.")

    root = Path(__file__).resolve().parent
    btc_path = root / "docs/runs/baseline-v1-2026-07-26/raw_candles.csv"
    btc = _read_candles(btc_path)
    if args.eth_input:
        eth = _read_candles(args.eth_input)
    else:
        eth = fetch_daily_candles(
            product_id="ETH-USD",
            start_date="2016-05-23",
            cache_path=root / "data/ETH-USD_coinbase_daily.csv",
            refresh_all=args.refresh_eth,
            as_of=AS_OF,
        )
    manifest = create_experiment_run(btc, eth, args.output_dir)
    print(f"Esperimento completato: {manifest}")


if __name__ == "__main__":
    main()
