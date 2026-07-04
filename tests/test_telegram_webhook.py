from __future__ import annotations

import unittest
from os import environ
from unittest.mock import Mock, patch

import pandas as pd
from fastapi import BackgroundTasks, HTTPException

from telegram_webhook import (
    HELP_MESSAGE,
    SUBSCRIBED_MESSAGE,
    UNSUBSCRIBED_MESSAGE,
    STATUS_JSON_URL,
    TelegramCommand,
    build_daily_signal_message,
    build_live_signal_message,
    extract_command,
    fetch_github_status,
    process_command,
    subscriber_count,
    telegram_webhook,
    app,
)
from notifications.telegram import TelegramConfig


class TelegramWebhookTests(unittest.TestCase):
    def test_cors_is_limited_to_dashboard_origins(self) -> None:
        cors = next(
            middleware
            for middleware in app.user_middleware
            if middleware.cls.__name__ == "CORSMiddleware"
        )

        self.assertEqual(
            cors.kwargs["allow_origins"],
            [
                "https://giuse2003.github.io",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
            ],
        )
        self.assertEqual(cors.kwargs["allow_methods"], ["GET"])
        self.assertEqual(cors.kwargs["allow_headers"], ["Accept"])

    def test_extracts_command_and_sender_from_private_chat(self) -> None:
        update = {
            "message": {
                "chat": {"id": 123, "type": "private"},
                "from": {
                    "id": 456,
                    "username": "utente",
                    "first_name": "Mario",
                    "language_code": "it",
                },
                "text": "/segnale@BTC_Prudential_Signal_bot",
            }
        }

        command = extract_command(update)

        self.assertIsNotNone(command)
        self.assertEqual(command.command, "/segnale")
        self.assertEqual(command.chat_id, 123)
        self.assertEqual(command.user_id, 456)
        self.assertEqual(command.username, "utente")

    def test_ignores_commands_from_groups(self) -> None:
        update = {
            "message": {
                "chat": {"id": -123, "type": "group"},
                "text": "/iscrivimi",
            }
        }

        self.assertIsNone(extract_command(update))

    def test_start_deep_link_maps_to_subscribe(self) -> None:
        update = {
            "message": {
                "chat": {"id": 123, "type": "private"},
                "text": "/start iscrivimi",
            }
        }

        command = extract_command(update)

        self.assertIsNotNone(command)
        self.assertEqual(command.command, "/iscrivimi")

    def test_builds_daily_condition_layout_from_status_json(self) -> None:
        message = build_daily_signal_message(
            {
                "signal": "MANTIENI",
                "risk_level": "ALTO",
                "price_eur": 54169.0,
                "condition_groups": {
                    "buy": [
                        {"label": "prezzo sopra SMA200", "passed": False},
                        {"label": "RSI uguale o maggiore di 40", "passed": False},
                        {"label": "prezzo sopra quello di 7 giorni prima", "passed": True},
                        {"label": "volume sopra media 20 giorni", "passed": False},
                    ],
                    "sell": [
                        {
                            "label": "prezzo sotto SMA50 per 2 giorni consecutivi",
                            "passed": True,
                        }
                    ],
                },
            }
        )

        self.assertTrue(message.startswith("BTC Signal Guard DAILY!"))
        self.assertIn("Segnale: MANTIENI", message)
        self.assertIn("54.169 EUR", message)
        self.assertIn("âœ… 3.", message)
        self.assertIn("VENDI:\nâœ… 1.", message)
        self.assertNotIn("Rischio", message)
        self.assertNotIn("USD", message)

    def test_builds_live_condition_layout_from_chart_data(self) -> None:
        rows = [
            {
                "date": pd.Timestamp("2025-01-01") + pd.Timedelta(days=index),
                "close": 100.0,
                "volume": 1000.0,
            }
            for index in range(210)
        ]

        message = build_live_signal_message(
            rows,
            {
                "price_usd": 150.0,
                "price_eur": 130.0,
                "volume_24h_usd": 2500.0,
            },
        )

        self.assertTrue(message.startswith("BTC Signal Guard LIVE!"))
        self.assertIn("Segnale: ACQUISTA", message)
        self.assertIn("130 EUR", message)
        self.assertIn("âœ… 1.", message)
        self.assertIn("âœ… 2.", message)
        self.assertIn("âœ… 3.", message)
        self.assertIn("âœ… 4.", message)

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

    def test_webhook_queues_command_from_any_private_chat(self) -> None:
        background_tasks = BackgroundTasks()
        update = {
            "message": {
                "chat": {"id": 987, "type": "private"},
                "text": "/segnale",
            }
        }

        with patch.dict(
            environ,
            {
                "TELEGRAM_BOT_TOKEN": "test-token",
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
        self.assertEqual(background_tasks.tasks[0].args[1].chat_id, "987")

    def test_webhook_rejects_invalid_secret(self) -> None:
        with patch.dict(
            environ,
            {
                "TELEGRAM_BOT_TOKEN": "test-token",
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

    @patch("telegram_webhook.send_telegram_message")
    def test_subscribe_command_stores_user_and_confirms(self, mock_send: Mock) -> None:
        store = Mock()
        command = TelegramCommand(
            command="/iscrivimi",
            chat_id=123,
            user_id=456,
            username="utente",
            first_name="Mario",
            language_code="it",
        )
        cfg = TelegramConfig(bot_token="token", chat_id="123")

        process_command(command, cfg, store)

        subscriber = store.subscribe.call_args.args[0]
        self.assertEqual(subscriber.telegram_chat_id, 123)
        self.assertEqual(subscriber.telegram_user_id, 456)
        mock_send.assert_called_once_with(cfg, SUBSCRIBED_MESSAGE)

    @patch("telegram_webhook.send_telegram_message")
    def test_unsubscribe_command_disables_existing_user(self, mock_send: Mock) -> None:
        store = Mock()
        store.unsubscribe.return_value = True
        command = TelegramCommand(
            command="/disiscrivimi",
            chat_id=123,
            user_id=456,
            username=None,
            first_name=None,
            language_code=None,
        )
        cfg = TelegramConfig(bot_token="token", chat_id="123")

        process_command(command, cfg, store)

        store.unsubscribe.assert_called_once_with(123)
        mock_send.assert_called_once_with(cfg, UNSUBSCRIBED_MESSAGE)

    @patch("telegram_webhook.send_telegram_message")
    def test_help_lists_subscription_commands(self, mock_send: Mock) -> None:
        command = TelegramCommand(
            command="/help",
            chat_id=123,
            user_id=None,
            username=None,
            first_name=None,
            language_code=None,
        )
        cfg = TelegramConfig(bot_token="token", chat_id="123")

        process_command(command, cfg, None)

        self.assertIn("/iscrivimi", HELP_MESSAGE)
        self.assertIn("/disiscrivimi", HELP_MESSAGE)
        mock_send.assert_called_once_with(cfg, HELP_MESSAGE)

    @patch("telegram_webhook.SupabaseSubscriberStore")
    def test_subscriber_count_returns_only_aggregate(self, mock_store: Mock) -> None:
        mock_store.return_value.count_active.return_value = 7

        with patch.dict(
            environ,
            {
                "SUPABASE_URL": "https://project.supabase.co",
                "SUPABASE_SERVICE_ROLE_KEY": "secret-test-key",
            },
            clear=False,
        ):
            result = subscriber_count()

        self.assertEqual(result, {"active_subscribers": 7})
        self.assertEqual(list(result), ["active_subscribers"])

    def test_subscriber_count_requires_server_configuration(self) -> None:
        with patch.dict(
            environ,
            {
                "SUPABASE_URL": "",
                "SUPABASE_SERVICE_ROLE_KEY": "",
            },
            clear=False,
        ):
            with self.assertRaises(HTTPException) as error:
                subscriber_count()

        self.assertEqual(error.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()

