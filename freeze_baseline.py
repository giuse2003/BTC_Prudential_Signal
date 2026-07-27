"""Crea un nuovo pacchetto baseline congelato."""

from __future__ import annotations

import argparse
from pathlib import Path

from data.coinbase import fetch_daily_candles
from reproducibility import create_frozen_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Congela un baseline BTC-USD riproducibile.")
    parser.add_argument("--as-of", required=True, help="Ultima candela inclusa, formato YYYY-MM-DD")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--source-tag")
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()

    candles = fetch_daily_candles(
        as_of=args.as_of,
        refresh_all=args.force_download,
    )
    manifest = create_frozen_run(
        candles,
        as_of=args.as_of,
        output_dir=args.output,
        run_id=args.run_id,
        source_tag=args.source_tag,
    )
    print(f"Baseline congelato: {manifest}")


if __name__ == "__main__":
    main()
