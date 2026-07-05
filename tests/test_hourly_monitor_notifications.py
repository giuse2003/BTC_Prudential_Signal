from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests

from hourly_monitor import (
    broadcast_to_subscribers,
    should_force_daily_download,
    should_notify,
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

    def test_first_run_saves_baseline_without_notification(self) -> None:
        must_notify, reason = should_notify(
            MonitorState(),
            signal="MANTIENI",
            conditions_key="BUY:00100|SELL:0",
        )

        self.assertFalse(must_notify)
        self.assertEqual(reason, "baseline iniziale salvata senza notifica")

    def test_unchanged_signal_and_conditions_do_not_notify(self) -> None:
        must_notify, reason = should_notify(
            MonitorState(
                last_signal="MANTIENI",
                last_conditions_key="BUY:00100|SELL:0",
            ),
            signal="MANTIENI",
            conditions_key="BUY:00100|SELL:0",
        )

        self.assertFalse(must_notify)
        self.assertEqual(reason, "segnale e condizioni invariati")

    def test_condition_change_notifies_even_when_signal_is_unchanged(self) -> None:
        must_notify, reason = should_notify(
            MonitorState(
                last_signal="MANTIENI",
                last_conditions_key="BUY:00100|SELL:0",
            ),
            signal="MANTIENI",
            conditions_key="BUY:00110|SELL:0",
        )

        self.assertTrue(must_notify)
        self.assertEqual(reason, "condizioni operative cambiate")

    def test_signal_change_notifies(self) -> None:
        must_notify, reason = should_notify(
            MonitorState(
                last_signal="MANTIENI",
                last_conditions_key="BUY:00100|SELL:0",
            ),
            signal="VENDI",
            conditions_key="BUY:00100|SELL:1",
        )

        self.assertTrue(must_notify)
        self.assertEqual(reason, "segnale cambiato: MANTIENI -> VENDI")


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


if __name__ == "__main__":
    unittest.main()
