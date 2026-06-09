from __future__ import annotations

import unittest

import pandas as pd

from strategy.signals import format_telegram_message


class TelegramMessageTests(unittest.TestCase):
    def test_message_contains_only_eur_price_and_no_summary(self) -> None:
        df = pd.DataFrame(
            {
                "Close_EUR": [54169.0],
                "Segnale": ["MANTIENI"],
                "Livello_Rischio": ["ALTO"],
            }
        )

        message = format_telegram_message(df, price_eur=54169.0)

        self.assertEqual(
            message,
            "\n".join(
                [
                    "BTC MONITOR",
                    "",
                    "Segnale: MANTIENI",
                    "Rischio: ALTO",
                    "",
                    "Prezzo:",
                    "54.169 EUR",
                    "",
                    "Indicazione:",
                    "Attendere. Nessuna nuova operazione consigliata.",
                ]
            ),
        )
        self.assertNotIn("USD", message)
        self.assertNotIn("Sintesi", message)

    def test_message_uses_historical_eur_price_as_fallback(self) -> None:
        df = pd.DataFrame(
            {
                "Close_EUR": [50000.0],
                "Segnale": ["ACQUISTA"],
                "Livello_Rischio": ["BASSO"],
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
            "msg = format_telegram_message(df_sig, price_eur=spot_eur)",
            source,
        )


if __name__ == "__main__":
    unittest.main()
