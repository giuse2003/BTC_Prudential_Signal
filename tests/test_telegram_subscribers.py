from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from telegram_subscribers import SupabaseSubscriberStore, TelegramSubscriber


class SupabaseSubscriberStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SupabaseSubscriberStore(
            "https://project.supabase.co/",
            "service-role-test-key",
        )

    @patch("telegram_subscribers.requests.post")
    def test_subscribe_uses_upsert_on_chat_id(self, mock_post: Mock) -> None:
        mock_post.return_value = Mock()
        subscriber = TelegramSubscriber(
            telegram_chat_id=123,
            telegram_user_id=456,
            telegram_username="utente",
            telegram_first_name="Mario",
            telegram_language_code="it",
        )

        self.store.subscribe(subscriber)

        _, kwargs = mock_post.call_args
        self.assertEqual(
            kwargs["params"],
            {"on_conflict": "telegram_chat_id"},
        )
        self.assertIn("resolution=merge-duplicates", kwargs["headers"]["Prefer"])
        self.assertEqual(kwargs["json"]["telegram_chat_id"], 123)
        self.assertTrue(kwargs["json"]["active"])
        self.assertIsNone(kwargs["json"]["unsubscribed_at"])
        mock_post.return_value.raise_for_status.assert_called_once_with()

    @patch("telegram_subscribers.requests.patch")
    def test_unsubscribe_returns_true_when_row_exists(self, mock_patch: Mock) -> None:
        response = Mock()
        response.json.return_value = [{"telegram_chat_id": 123}]
        mock_patch.return_value = response

        removed = self.store.unsubscribe(123)

        self.assertTrue(removed)
        _, kwargs = mock_patch.call_args
        self.assertEqual(kwargs["params"]["telegram_chat_id"], "eq.123")
        self.assertFalse(kwargs["json"]["active"])
        response.raise_for_status.assert_called_once_with()

    @patch("telegram_subscribers.requests.patch")
    def test_unsubscribe_returns_false_when_row_is_missing(
        self,
        mock_patch: Mock,
    ) -> None:
        response = Mock()
        response.json.return_value = []
        mock_patch.return_value = response

        self.assertFalse(self.store.unsubscribe(999))

    @patch("telegram_subscribers.requests.get")
    def test_count_active_uses_server_side_exact_count(self, mock_get: Mock) -> None:
        response = Mock()
        response.headers = {"Content-Range": "0-0/12"}
        mock_get.return_value = response

        count = self.store.count_active()

        self.assertEqual(count, 12)
        _, kwargs = mock_get.call_args
        self.assertEqual(kwargs["params"]["active"], "eq.true")
        self.assertEqual(kwargs["headers"]["Prefer"], "count=exact")
        self.assertEqual(kwargs["headers"]["Range"], "0-0")
        response.raise_for_status.assert_called_once_with()

    @patch("telegram_subscribers.requests.get")
    def test_count_active_supports_empty_table(self, mock_get: Mock) -> None:
        response = Mock()
        response.headers = {"Content-Range": "*/0"}
        mock_get.return_value = response

        self.assertEqual(self.store.count_active(), 0)


if __name__ == "__main__":
    unittest.main()
