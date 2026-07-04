from __future__ import annotations

import unittest

from notifications.telegram import extract_authorized_commands, format_monitor_message
from telegram_command import build_signal_message


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

    def test_command_signal_uses_daily_condition_layout(self) -> None:
        message = build_signal_message(
            {
                "signal": "VENDI",
                "price_eur": 56316.0,
                "condition_groups": {
                    "buy": [
                        {"passed": False},
                        {"passed": False},
                        {"passed": False},
                        {"passed": False},
                    ],
                    "sell": [{"passed": True}],
                },
            },
            price_eur=56316.0,
        )

        self.assertTrue(message.startswith("BTC Signal Guard DAILY!"))
        self.assertIn("56.316 EUR", message)
        self.assertIn("ACQUISTA:\n🅾️ 1.", message)
        self.assertIn("VENDI:\n✅ 1.", message)
        self.assertNotIn("Rischio", message)


if __name__ == "__main__":
    unittest.main()
