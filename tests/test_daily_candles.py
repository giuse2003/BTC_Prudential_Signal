from __future__ import annotations

import unittest

import pandas as pd

from data.daily_candles import keep_closed_daily_candles


class ClosedDailyCandlesTests(unittest.TestCase):
    def test_excludes_current_utc_day(self) -> None:
        df = pd.DataFrame(
            {"Close": [100.0, 110.0, 120.0]},
            index=pd.to_datetime(["2026-06-06", "2026-06-07", "2026-06-08"]),
        )

        result = keep_closed_daily_candles(
            df,
            now_utc=pd.Timestamp("2026-06-08 14:00:00", tz="UTC"),
        )

        self.assertEqual(list(result.index), list(df.index[:2]))

    def test_accepts_timezone_aware_index(self) -> None:
        df = pd.DataFrame(
            {"Close": [100.0, 110.0]},
            index=pd.to_datetime(["2026-06-07", "2026-06-08"], utc=True),
        )

        result = keep_closed_daily_candles(
            df,
            now_utc=pd.Timestamp("2026-06-08 01:00:00", tz="UTC"),
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result.index[0], pd.Timestamp("2026-06-07", tz="UTC"))


if __name__ == "__main__":
    unittest.main()
