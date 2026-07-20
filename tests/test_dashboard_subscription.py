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
            "https://btc-prudential-signal.giuse2003.workers.dev/subscribers/count",
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

    def test_dashboard_renders_daily_ohlc_candles_with_live_coinbase_row(self) -> None:
        self.assertIn("api.exchange.coinbase.com/products/BTC-USD/candles", self.javascript)
        self.assertIn("function drawCandlesticks", self.javascript)
        self.assertIn("provisional: true", self.javascript)
        self.assertIn("legend-candle-up", self.html)
        self.assertIn("legend-candle-down", self.html)
        self.assertIn("legend-candle-live", self.html)
        self.assertNotIn('drawLine(ctx, rows, "close"', self.javascript)

    def test_dashboard_defaults_to_six_month_chart_range(self) -> None:
        self.assertIn('data-range="180">6 mesi', self.html)
        self.assertIn('let chartRange = "180"', self.javascript)


if __name__ == "__main__":
    unittest.main()
