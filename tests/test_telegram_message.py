from __future__ import annotations

import unittest

import pandas as pd

from strategy.signals import format_telegram_message


class TelegramMessageTests(unittest.TestCase):
    def test_message_uses_compact_condition_layout(self) -> None:
        df = pd.DataFrame(
            {
                "Close_EUR": [54169.0, 54169.0],
                "Close": [120.0, 90.0],
                "SMA50": [100.0, 100.0],
                "SMA200": [100.0, 100.0],
                "RSI": [42.0, 39.0],
                "Volume": [900.0, 800.0],
                "VolumeAvg20": [1000.0, 1000.0],
                "Close_7d_ago": [110.0, 95.0],
                "Segnale": ["MANTIENI", "VENDI"],
                "Livello_Rischio": ["MEDIO", "ALTO"],
            }
        )

        message = format_telegram_message(df, price_eur=54169.0)

        self.assertEqual(
            message,
            "\n".join(
                [
                    "BTC MONITOR",
                    "",
                    "Segnale: VENDI",
                    "",
                    "Prezzo:",
                    "54.169 EUR",
                    "",
                    "(per le condizioni: /conditions)",
                    "",
                    "ACQUISTA:",
                    "🅾️ 1.",
                    "🅾️ 2.",
                    "🅾️ 3.",
                    "🅾️ 4.",
                    "🅾️ 5.",
                    "",
                    "VENDI:",
                    "🅾️ 1.",
                ]
            ),
        )
        self.assertNotIn("USD", message)
        self.assertNotIn("Sintesi", message)
        self.assertNotIn("Rischio", message)
        self.assertNotIn("Indicazione", message)

    def test_message_uses_historical_eur_price_as_fallback(self) -> None:
        df = pd.DataFrame(
            {
                "Close_EUR": [50000.0, 50000.0],
                "Close": [120.0, 130.0],
                "SMA50": [110.0, 115.0],
                "SMA200": [100.0, 100.0],
                "RSI": [45.0, 50.0],
                "Volume": [2000.0, 2100.0],
                "VolumeAvg20": [1000.0, 1000.0],
                "Close_7d_ago": [110.0, 120.0],
                "Segnale": ["ACQUISTA", "ACQUISTA"],
                "Livello_Rischio": ["BASSO", "BASSO"],
            }
        )

        message = format_telegram_message(df)

        self.assertIn("50.000 EUR", message)

    def test_manual_preview_uses_same_formatter_as_signal_change(self) -> None:
        source = (
            __import__("pathlib")
            .Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("hourly_monitor.py")
            .read_text(encoding="utf-8")
        )

        self.assertNotIn("BTC Monitor attivo e funzionante.", source)
        self.assertIn(
            'msg = format_telegram_message(df_sig, price_eur=spot_eur, title="BTC MONITOR DAILY!")',
            source,
        )

    def test_message_accepts_custom_title(self) -> None:
        df = pd.DataFrame(
            {
                "Close_EUR": [50000.0, 50000.0],
                "Close": [120.0, 90.0],
                "SMA50": [100.0, 100.0],
                "SMA200": [100.0, 100.0],
                "RSI": [42.0, 39.0],
                "Volume": [900.0, 800.0],
                "VolumeAvg20": [1000.0, 1000.0],
                "Close_7d_ago": [110.0, 95.0],
                "Segnale": ["MANTIENI", "VENDI"],
                "Livello_Rischio": ["MEDIO", "ALTO"],
            }
        )

        message = format_telegram_message(df, price_eur=50000.0, title="BTC MONITOR LIVE!")

        self.assertTrue(message.startswith("BTC MONITOR LIVE!"))

    def test_manual_workflow_dispatch_still_forces_telegram_response(self) -> None:
        source = (
            __import__("pathlib")
            .Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("hourly_monitor.py")
            .read_text(encoding="utf-8")
        )

        self.assertIn("must_notify = is_manual_run or scheduled_notify", source)
        self.assertIn('notify_reason = "richiesta manuale workflow_dispatch"', source)


if __name__ == "__main__":
    unittest.main()
