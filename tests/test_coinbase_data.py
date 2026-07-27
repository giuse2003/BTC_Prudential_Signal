from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from data.coinbase import fetch_daily_candles, validate_daily_candles


def candle_frame(dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [100.0] * len(dates),
            "High": [110.0] * len(dates),
            "Low": [90.0] * len(dates),
            "Close": [105.0] * len(dates),
            "Volume": [10.0] * len(dates),
        },
        index=pd.to_datetime(dates),
    )


class CoinbaseDataTests(unittest.TestCase):
    def test_rejects_missing_calendar_day(self) -> None:
        with self.assertRaisesRegex(ValueError, "Mancano 1 candele"):
            validate_daily_candles(candle_frame(["2026-07-20", "2026-07-22"]))

    def test_uses_coinbase_cache_when_refresh_is_temporarily_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "BTC-USD_coinbase_daily.csv"
            cached = candle_frame(["2026-07-20", "2026-07-21"])
            cached.index.name = "Date"
            cached.to_csv(path)
            with patch("data.coinbase._download_candles", side_effect=RuntimeError("offline")):
                result = fetch_daily_candles(
                    cache_path=path,
                    start_date="2026-07-20",
                    now_utc=pd.Timestamp("2026-07-23", tz="UTC"),
                )
        self.assertEqual(list(result.index), list(pd.to_datetime(["2026-07-20", "2026-07-21"])))

    def test_excludes_current_utc_candle(self) -> None:
        downloaded = candle_frame(["2026-07-20", "2026-07-21", "2026-07-22"])
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("data.coinbase._download_candles", return_value=downloaded):
                result = fetch_daily_candles(
                    cache_path=Path(tmp_dir) / "cache.csv",
                    start_date="2026-07-20",
                    now_utc=pd.Timestamp("2026-07-22 12:00", tz="UTC"),
                )
        self.assertEqual(result.index[-1], pd.Timestamp("2026-07-21"))


if __name__ == "__main__":
    unittest.main()
