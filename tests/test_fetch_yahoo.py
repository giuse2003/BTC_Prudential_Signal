from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from data.fetch_yahoo import fetch_btc_daily_csv


class FetchYahooTests(unittest.TestCase):
    def test_required_symbol_uses_existing_csv_when_download_returns_no_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "BTC-USD_daily.csv"
            csv_path.write_text("Date,Close\n2026-06-21,100\n", encoding="utf-8")

            with (
                patch("data.fetch_yahoo._default_output_path", return_value=csv_path),
                patch("data.fetch_yahoo.yf.download", return_value=pd.DataFrame()),
            ):
                result = fetch_btc_daily_csv(
                    symbol="BTC-USD",
                    force_download=True,
                    is_optional=False,
                )

        self.assertEqual(result, csv_path)

    def test_required_symbol_raises_when_download_fails_without_existing_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "BTC-USD_daily.csv"

            with (
                patch("data.fetch_yahoo._default_output_path", return_value=csv_path),
                patch("data.fetch_yahoo.yf.download", return_value=pd.DataFrame()),
            ):
                with self.assertRaises(RuntimeError):
                    fetch_btc_daily_csv(
                        symbol="BTC-USD",
                        force_download=True,
                        is_optional=False,
                    )


if __name__ == "__main__":
    unittest.main()
