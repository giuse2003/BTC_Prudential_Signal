from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from notifications.telegram import extract_authorized_commands, format_monitor_message
from telegram_command import build_live_signal_message


class TelegramCommandTests(unittest.TestCase):
    def test_extracts_only_commands_from_authorized_chat(self) -> None:
        updates = [
            {
                "update_id": 10,
                "message": {"chat": {"id": 123}, "text": "/segnale"},
            },
            {
                "update_id": 11,
                "message": {"chat": {"id": 999}, "text": "/segnale"},
            },
            {
                "update_id": 12,
                "message": {"chat": {"id": 123}, "text": "/HELP altro"},
            },
        ]

        commands, next_offset = extract_authorized_commands(updates, "123")

        self.assertEqual(commands, ["/segnale", "/help"])
        self.assertEqual(next_offset, 13)

    def test_normalizes_command_with_bot_username(self) -> None:
        updates = [
            {
                "update_id": 20,
                "message": {
                    "chat": {"id": "123"},
                    "text": "/segnale@BTC_Prudential_Signal_bot",
                },
            }
        ]

        commands, _ = extract_authorized_commands(updates, "123")

        self.assertEqual(commands, ["/segnale"])

    def test_shared_formatter_preserves_requested_layout(self) -> None:
        message = format_monitor_message("MANTIENI", "ALTO", 54169.0)

        self.assertIn("54.169 EUR", message)
        self.assertNotIn("USD", message)
        self.assertNotIn("Sintesi", message)

    @patch("telegram_command.live_condition_statuses", return_value=([False] * 4, [True]))
    @patch("telegram_command.build_live_signal_frame")
    @patch("telegram_command.fetch_btc_market")
    def test_command_signal_uses_live_condition_layout(
        self,
        fetch_market,
        build_frame,
        _condition_statuses,
    ) -> None:
        fetch_market.return_value.price_usd = 60000.0
        fetch_market.return_value.price_eur = 56316.0
        fetch_market.return_value.volume_24h_usd = 1000.0
        build_frame.return_value = pd.DataFrame({"Close": [60000.0]})
        rows = [
            {"date": "2026-07-20", "close": 59000.0, "volume": 900.0},
            {"date": "2026-07-21", "close": 59500.0, "volume": 950.0},
        ]

        message = build_live_signal_message(rows)

        self.assertTrue(message.startswith("BTC Signal Guard LIVE!"))
        self.assertIn("56.316 EUR", message)
        self.assertIn("ACQUISTA:\n🅾️ 1.", message)
        self.assertIn("VENDI:\n✅ 1.", message)
        self.assertNotIn("Rischio", message)

    def test_worker_has_no_daily_signal_code(self) -> None:
        source = (
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("cloudflare-worker", "src", "worker.js")
            .read_text(encoding="utf-8")
        )

        self.assertNotIn("buildDailySignalMessage", source)
        self.assertNotIn("BTC MONITOR DAILY!", source)
        self.assertNotIn("fetchGithubStatus", source)


if __name__ == "__main__":
    unittest.main()
