from __future__ import annotations

import unittest
from os import environ
from unittest.mock import Mock, patch

from fastapi import BackgroundTasks, HTTPException

from telegram_webhook import (
    STATUS_JSON_URL,
    build_signal_message,
    extract_command,
    fetch_github_status,
    telegram_webhook,
)


class TelegramWebhookTests(unittest.TestCase):
    def test_extracts_command_only_from_authorized_chat(self) -> None:
        update = {
            "message": {
                "chat": {"id": 123},
                "text": "/segnale@BTC_Prudential_Signal_bot",
            }
        }

        self.assertEqual(extract_command(update, "123"), "/segnale")
        self.assertIsNone(extract_command(update, "999"))

    def test_builds_existing_monitor_layout_from_status_json(self) -> None:
        message = build_signal_message(
            {
                "signal": "MANTIENI",
                "risk_level": "ALTO",
                "price_eur": 54169.0,
            }
        )

        self.assertIn("Segnale: MANTIENI", message)
        self.assertIn("Rischio: ALTO", message)
        self.assertIn("54.169 EUR", message)
        self.assertNotIn("USD", message)

    @patch("telegram_webhook.requests.get")
    def test_fetches_status_from_mandatory_github_raw_url(self, mock_get: Mock) -> None:
        response = Mock()
        response.json.return_value = {"signal": "ACQUISTA"}
        mock_get.return_value = response

        status = fetch_github_status()

        self.assertEqual(status["signal"], "ACQUISTA")
        mock_get.assert_called_once_with(
            STATUS_JSON_URL,
            headers={
                "Accept": "application/json",
                "Cache-Control": "no-cache",
            },
            timeout=8,
        )
        response.raise_for_status.assert_called_once_with()

    def test_webhook_queues_authorized_command(self) -> None:
        background_tasks = BackgroundTasks()
        update = {"message": {"chat": {"id": 123}, "text": "/segnale"}}

        with patch.dict(
            environ,
            {
                "TELEGRAM_BOT_TOKEN": "test-token",
                "TELEGRAM_CHAT_ID": "123",
                "TELEGRAM_WEBHOOK_SECRET": "test-secret",
            },
            clear=False,
        ):
            result = telegram_webhook(
                update,
                background_tasks,
                x_telegram_bot_api_secret_token="test-secret",
            )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(len(background_tasks.tasks), 1)

    def test_webhook_rejects_invalid_secret(self) -> None:
        with patch.dict(
            environ,
            {
                "TELEGRAM_BOT_TOKEN": "test-token",
                "TELEGRAM_CHAT_ID": "123",
                "TELEGRAM_WEBHOOK_SECRET": "expected-secret",
            },
            clear=False,
        ):
            with self.assertRaises(HTTPException) as error:
                telegram_webhook(
                    {"message": {"chat": {"id": 123}, "text": "/segnale"}},
                    BackgroundTasks(),
                    x_telegram_bot_api_secret_token="wrong-secret",
                )

        self.assertEqual(error.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
