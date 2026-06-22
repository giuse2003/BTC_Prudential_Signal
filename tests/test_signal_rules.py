from __future__ import annotations

import unittest

import pandas as pd

from strategy.signals import build_live_signal_frame, compute_signals, live_condition_statuses


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

    def test_live_signal_recomputes_indicators_with_live_price_and_volume(self) -> None:
        dates = pd.date_range("2026-01-01", periods=210, freq="D")
        df = pd.DataFrame(
            {
                "Open": [100.0] * 210,
                "High": [101.0] * 210,
                "Low": [99.0] * 210,
                "Close": [100.0] * 210,
                "Volume": [1000.0] * 210,
            },
            index=dates,
        )

        result = build_live_signal_frame(
            df,
            live_price_usd=150.0,
            live_volume_24h=2500.0,
            live_time_utc=pd.Timestamp("2026-08-01 12:00:00", tz="UTC"),
        )
        buy_statuses, sell_statuses = live_condition_statuses(result)

        self.assertEqual(result.index[-1], pd.Timestamp("2026-08-01"))
        self.assertEqual(result.iloc[-1]["Close"], 150.0)
        self.assertEqual(result.iloc[-1]["Volume"], 2500.0)
        self.assertEqual(result.iloc[-1]["VolumeAvg20"], 1000.0)
        self.assertTrue(buy_statuses[0])
        self.assertTrue(buy_statuses[2])
        self.assertTrue(buy_statuses[3])
        self.assertTrue(buy_statuses[4])
        self.assertFalse(sell_statuses[0])


if __name__ == "__main__":
    unittest.main()
