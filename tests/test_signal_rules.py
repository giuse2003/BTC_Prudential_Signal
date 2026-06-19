from __future__ import annotations

import unittest

import pandas as pd

from strategy.signals import compute_signals


class SignalRulesTests(unittest.TestCase):
    def test_buy_keeps_five_conditions_and_allows_rsi_above_65(self) -> None:
        df = pd.DataFrame(
            {
                "Close": [120.0],
                "SMA50": [110.0],
                "SMA200": [100.0],
                "RSI": [72.0],
                "Volume": [2000.0],
                "VolumeAvg20": [1000.0],
                "Close_7d_ago": [115.0],
            }
        )

        result = compute_signals(df)

        self.assertEqual(result.iloc[-1]["Segnale"], "ACQUISTA")

    def test_price_below_sma50_for_two_days_triggers_sell_signal(self) -> None:
        df = pd.DataFrame(
            {
                "Close": [120.0, 119.0],
                "SMA50": [130.0, 128.0],
                "SMA200": [100.0, 100.0],
                "RSI": [55.0, 56.0],
                "Volume": [800.0, 850.0],
                "VolumeAvg20": [1000.0, 1000.0],
                "Close_7d_ago": [110.0, 111.0],
            }
        )

        result = compute_signals(df)

        self.assertEqual(result.iloc[-1]["Segnale"], "VENDI")

    def test_single_close_below_sma50_does_not_trigger_sell_signal(self) -> None:
        df = pd.DataFrame(
            {
                "Close": [132.0, 119.0],
                "SMA50": [130.0, 128.0],
                "SMA200": [100.0, 100.0],
                "RSI": [55.0, 56.0],
                "Volume": [800.0, 850.0],
                "VolumeAvg20": [1000.0, 1000.0],
                "Close_7d_ago": [110.0, 111.0],
            }
        )

        result = compute_signals(df)

        self.assertEqual(result.iloc[-1]["Segnale"], "MANTIENI")


if __name__ == "__main__":
    unittest.main()
