from __future__ import annotations

import unittest

import pandas as pd

from experiments.candidate_evaluation import (
    VARIANTS,
    _moving_block_bootstrap,
    build_signals,
    strategy_path,
)
from strategy.rules import ACTION_BUY, ACTION_HOLD, ACTION_SELL


def signal_frame() -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=4, freq="D")
    return pd.DataFrame(
        {
            "Close": [110.0, 105.0, 95.0, 94.0],
            "SMA50": [100.0, 100.0, 100.0, 100.0],
            "SMA200": [90.0, 90.0, 90.0, 90.0],
            "RSI": [50.0, 50.0, 50.0, 50.0],
            "Close_7d_ago": [100.0, 100.0, 100.0, 100.0],
            "Volume": [80.0, 120.0, 120.0, 120.0],
            "VolumeAvg20": [100.0, 100.0, 100.0, 100.0],
        },
        index=index,
    )


class CandidateEvaluationTests(unittest.TestCase):
    def test_b1_buys_when_only_volume_condition_fails(self) -> None:
        frame = signal_frame()
        baseline = build_signals(frame, VARIANTS[0])
        candidate = build_signals(frame, VARIANTS[2])

        self.assertEqual(baseline.iloc[0], ACTION_HOLD)
        self.assertEqual(candidate.iloc[0], ACTION_BUY)

    def test_s1_sells_after_first_close_below_sma50(self) -> None:
        frame = signal_frame()
        baseline = build_signals(frame, VARIANTS[0])
        candidate = build_signals(frame, VARIANTS[1])

        self.assertNotEqual(baseline.iloc[2], ACTION_SELL)
        self.assertEqual(candidate.iloc[2], ACTION_SELL)
        self.assertEqual(baseline.iloc[3], ACTION_SELL)

    def test_transaction_cost_reduces_equity_when_exposure_changes(self) -> None:
        frame = signal_frame()
        signals = pd.Series(
            [ACTION_BUY, ACTION_HOLD, ACTION_SELL, ACTION_HOLD],
            index=frame.index,
        )
        gross = strategy_path(frame, signals, 0.0)
        net = strategy_path(frame, signals, 0.006)

        self.assertLess(net["Equity"].iloc[-1], gross["Equity"].iloc[-1])
        self.assertEqual(net["TurnoverSides"].sum(), 2.0)

    def test_bootstrap_is_deterministic(self) -> None:
        difference = pd.Series([0.01, -0.005, 0.002] * 20)
        first = _moving_block_bootstrap(difference, samples=100, block_days=5, seed=7)
        second = _moving_block_bootstrap(difference, samples=100, block_days=5, seed=7)

        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
