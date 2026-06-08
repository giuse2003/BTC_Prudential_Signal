from __future__ import annotations

import unittest

import pandas as pd

from backtest.backtest import run_backtest
from config import CFG


class BacktestMetricsTests(unittest.TestCase):
    def test_uses_crypto_calendar_for_annualized_return(self) -> None:
        index = pd.date_range("2026-01-01", periods=366, freq="D")
        close = pd.Series(
            [100.0 * (2.0 ** (i / 365.0)) for i in range(366)],
            index=index,
        )
        df = pd.DataFrame({"Close": close, "Segnale": "MANTIENI"})

        _, _, metrics_bh = run_backtest(df)

        self.assertEqual(CFG.periods_per_year, 365)
        self.assertAlmostEqual(metrics_bh.annualized_return, 1.0, places=10)

    def test_counts_only_completed_trades_in_win_rate(self) -> None:
        index = pd.date_range("2026-01-01", periods=9, freq="D")
        df = pd.DataFrame(
            {
                "Close": [100, 100, 110, 110, 100, 90, 90, 100, 110],
                "Segnale": [
                    "ACQUISTA",
                    "MANTIENI",
                    "VENDI",
                    "ACQUISTA",
                    "MANTIENI",
                    "VENDI",
                    "ACQUISTA",
                    "MANTIENI",
                    "MANTIENI",
                ],
            },
            index=index,
        )

        _, metrics, _ = run_backtest(df)

        self.assertEqual(metrics.num_operations, 2)
        self.assertAlmostEqual(metrics.win_rate, 0.5)

    def test_open_position_is_not_a_completed_trade(self) -> None:
        index = pd.date_range("2026-01-01", periods=4, freq="D")
        df = pd.DataFrame(
            {
                "Close": [100, 105, 110, 115],
                "Segnale": ["ACQUISTA", "MANTIENI", "MANTIENI", "MANTIENI"],
            },
            index=index,
        )

        _, metrics, _ = run_backtest(df)

        self.assertEqual(metrics.num_operations, 0)
        self.assertEqual(metrics.win_rate, 0.0)


if __name__ == "__main__":
    unittest.main()
