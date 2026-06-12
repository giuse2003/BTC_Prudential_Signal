from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DashboardSubscriptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = (PROJECT_ROOT / "docs" / "index.html").read_text(
            encoding="utf-8"
        )
        self.javascript = (PROJECT_ROOT / "docs" / "app.js").read_text(
            encoding="utf-8"
        )

    def test_dashboard_contains_telegram_subscription_card(self) -> None:
        self.assertIn("Notifiche Telegram", self.html)
        self.assertIn("Iscriviti su Telegram", self.html)
        self.assertIn(
            "https://t.me/BTC_Prudential_Signal_bot?start=iscrivimi",
            self.html,
        )

    def test_dashboard_uses_safe_public_count_endpoint_and_fallback(self) -> None:
        self.assertIn(
            "https://btc-prudential-signal.onrender.com/subscribers/count",
            self.javascript,
        )
        self.assertIn("Iscritti attivi: non disponibile", self.javascript)
        self.assertIn("active_subscribers", self.javascript)

    def test_public_frontend_does_not_reference_backend_secrets(self) -> None:
        public_code = self.html + self.javascript
        forbidden_names = (
            "SUPABASE_SERVICE_ROLE_KEY",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_WEBHOOK_SECRET",
        )
        for name in forbidden_names:
            self.assertNotIn(name, public_code)


if __name__ == "__main__":
    unittest.main()
