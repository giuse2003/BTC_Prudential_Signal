from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from hourly_monitor import (
    broadcast_to_subscribers,
    should_force_daily_download,
)
from state.state_store import MonitorState


class HourlyMonitorNotificationTests(unittest.TestCase):
    def test_forces_daily_download_until_expected_candle_is_processed(self) -> None:
        self.assertTrue(
            should_force_daily_download(
                MonitorState(last_processed_candle_date="2026-07-03"),
                expected_closed_candle_date="2026-07-04",
            )
        )

    def test_uses_cache_after_expected_candle_is_processed(self) -> None:
        self.assertFalse(
            should_force_daily_download(
                MonitorState(last_processed_candle_date="2026-07-04"),
                expected_closed_candle_date="2026-07-04",
            )
        )

    def test_manual_run_forces_daily_download_even_after_processing(self) -> None:
        self.assertTrue(
            should_force_daily_download(
                MonitorState(last_processed_candle_date="2026-07-04"),
                expected_closed_candle_date="2026-07-04",
                is_manual_run=True,
            )
        )

    def test_monitor_has_no_daily_telegram_send_path(self) -> None:
        source = (
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("hourly_monitor.py")
            .read_text(encoding="utf-8")
        )

        self.assertNotIn("should_notify", source)
        self.assertNotIn("BTC Signal Guard DAILY!", source)
        self.assertNotIn("broadcast DAILY", source)
        self.assertEqual(source.count("send_telegram_message(cfg, live_msg)"), 1)

    def test_local_analysis_does_not_send_telegram_messages(self) -> None:
        source = (
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath("main.py")
            .read_text(encoding="utf-8")
        )

        self.assertNotIn("send_telegram_message", source)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", source)


class BroadcastToSubscribersTests(unittest.TestCase):
    @patch("hourly_monitor.SupabaseSubscriberStore")
    @patch("hourly_monitor.send_telegram_message")
    def test_broadcast_sends_to_all_active_and_updates_status(
        self,
        mock_send: Mock,
        mock_store_cls: Mock,
    ) -> None:
        mock_store = Mock()
        mock_store_cls.return_value = mock_store
        
        from telegram_subscribers import TelegramSubscriber
        mock_store.get_active_subscribers.return_value = [
            TelegramSubscriber(telegram_chat_id=111, telegram_user_id=1, telegram_username="u1", telegram_first_name="A", telegram_language_code="it"),
            TelegramSubscriber(telegram_chat_id=222, telegram_user_id=2, telegram_username="u2", telegram_first_name="B", telegram_language_code="it"),
        ]
        
        broadcast_to_subscribers("bot-token", "https://url.supabase.co", "key", "Hello world")
        
        self.assertEqual(mock_send.call_count, 2)
        send_calls = mock_send.call_args_list
        self.assertEqual(send_calls[0][0][0].chat_id, "111")
        self.assertEqual(send_calls[1][0][0].chat_id, "222")
        self.assertEqual(send_calls[0][0][1], "Hello world")
        
        self.assertEqual(mock_store.update_delivery_status.call_count, 2)
        mock_store.update_delivery_status.assert_any_call(111, success=True)
        mock_store.update_delivery_status.assert_any_call(222, success=True)

    @patch("hourly_monitor.SupabaseSubscriberStore")
    @patch("hourly_monitor.send_telegram_message")
    def test_broadcast_skips_excluded_chat_id(
        self,
        mock_send: Mock,
        mock_store_cls: Mock,
    ) -> None:
        mock_store = Mock()
        mock_store_cls.return_value = mock_store

        from telegram_subscribers import TelegramSubscriber
        mock_store.get_active_subscribers.return_value = [
            TelegramSubscriber(telegram_chat_id=111, telegram_user_id=1, telegram_username="admin", telegram_first_name="A", telegram_language_code="it"),
            TelegramSubscriber(telegram_chat_id=222, telegram_user_id=2, telegram_username="u2", telegram_first_name="B", telegram_language_code="it"),
        ]

        broadcast_to_subscribers(
            "bot-token",
            "https://url.supabase.co",
            "key",
            "Hello world",
            excluded_chat_ids={"111"},
        )

        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args[0][0].chat_id, "222")
        mock_store.update_delivery_status.assert_called_once_with(222, success=True)

    @patch("hourly_monitor.SupabaseSubscriberStore")
    @patch("hourly_monitor.send_telegram_message")
    def test_broadcast_handles_blocked_user_and_general_error(
        self,
        mock_send: Mock,
        mock_store_cls: Mock,
    ) -> None:
        mock_store = Mock()
        mock_store_cls.return_value = mock_store
        
        from telegram_subscribers import TelegramSubscriber
        mock_store.get_active_subscribers.return_value = [
            TelegramSubscriber(telegram_chat_id=111, telegram_user_id=1, telegram_username="u1", telegram_first_name="A", telegram_language_code="it"),
            TelegramSubscriber(telegram_chat_id=222, telegram_user_id=2, telegram_username="u2", telegram_first_name="B", telegram_language_code="it"),
            TelegramSubscriber(telegram_chat_id=333, telegram_user_id=3, telegram_username="u3", telegram_first_name="C", telegram_language_code="it"),
        ]
        
        err_response = Mock()
        err_response.status_code = 403
        err_response.text = "Forbidden: bot was blocked by the user"
        http_err = requests.exceptions.HTTPError("403 Forbidden", response=err_response)
        
        mock_send.side_effect = [
            None,
            http_err,
            RuntimeError("Network issue"),
        ]
        
        broadcast_to_subscribers("bot-token", "https://url.supabase.co", "key", "Hello world")
        
        self.assertEqual(mock_send.call_count, 3)
        self.assertEqual(mock_store.update_delivery_status.call_count, 3)
        
        mock_store.update_delivery_status.assert_any_call(111, success=True)
        mock_store.update_delivery_status.assert_any_call(
            222, success=False, error_msg="HTTP 403: Forbidden: bot was blocked by the user", block_detected=True
        )
        mock_store.update_delivery_status.assert_any_call(
            333, success=False, error_msg="Network issue", block_detected=False
        )


class WorkflowConcurrencyTests(unittest.TestCase):
    def test_hourly_monitor_workflow_serializes_runs(self) -> None:
        workflow = (
            Path(__file__)
            .resolve()
            .parents[1]
            .joinpath(".github", "workflows", "hourly-monitor.yml")
            .read_text(encoding="utf-8")
        )

        self.assertIn("concurrency:", workflow)
        self.assertIn("group: btc-signal-guard-monitor", workflow)
        self.assertIn("cancel-in-progress: false", workflow)


if __name__ == "__main__":
    unittest.main()
