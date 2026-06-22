from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from reports.generate import save_chart_data_json, save_live_status_json


class ChartDataJsonTests(unittest.TestCase):
    def test_saves_compact_chart_rows(self) -> None:
        df = pd.DataFrame(
            {
                "Close": [100.0],
                "SMA50": [90.0],
                "SMA200": [80.0],
                "RSI": [45.0],
                "Volume": [1000.0],
                "VolumeAvg20": [900.0],
                "Segnale": ["MANTIENI"],
            },
            index=pd.to_datetime(["2026-06-21"]),
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "chart-data.json"
            save_chart_data_json(df, path)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(
            payload,
            [
                {
                    "date": "2026-06-21",
                    "close": 100.0,
                    "sma50": 90.0,
                    "sma200": 80.0,
                    "rsi": 45.0,
                    "volume": 1000.0,
                    "volume_avg20": 900.0,
                    "signal": "MANTIENI",
                }
            ],
        )

    def test_saves_live_status_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "live-status.json"
            save_live_status_json(
                signal="VENDI",
                price_usd=64000.0,
                price_eur=56000.0,
                volume_24h_usd=27000000000.0,
                buy_statuses=[False, False, True, False, False],
                sell_statuses=[True],
                out_path=path,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["signal"], "VENDI")
        self.assertEqual(payload["price_eur"], 56000.0)
        self.assertTrue(payload["condition_groups"]["buy"][2]["passed"])
        self.assertTrue(payload["condition_groups"]["sell"][0]["passed"])


if __name__ == "__main__":
    unittest.main()
