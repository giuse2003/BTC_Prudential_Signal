"""Esegue l'esperimento BTC isolato sui candidati del modello."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from experiments.candidate_evaluation import AS_OF, create_experiment_run


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Valuta V1-S1 e V1-B1 esclusivamente su BTC-USD."
    )
    parser.add_argument("--as-of", default=AS_OF)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/experiments/btc-model-candidates-v1-2026-07-26"),
    )
    args = parser.parse_args()
    if args.as_of != AS_OF:
        raise ValueError(f"Il protocollo registrato richiede --as-of {AS_OF}.")

    root = Path(__file__).resolve().parent
    btc_path = root / "docs/runs/baseline-v1-2026-07-26/raw_candles.csv"
    btc = pd.read_csv(btc_path, parse_dates=["Date"], index_col="Date")
    manifest = create_experiment_run(btc, args.output_dir)
    print(f"Esperimento BTC completato: {manifest}")


if __name__ == "__main__":
    main()
