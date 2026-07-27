from __future__ import annotations

import re
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class CloudflareWorkerConditionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (
            PROJECT_ROOT / "cloudflare-worker" / "src" / "worker.js"
        ).read_text(encoding="utf-8")

    def test_conditions_command_lists_four_buy_conditions(self) -> None:
        match = re.search(
            r"const CONDITIONS_MESSAGE = \[(?P<body>.*?)\]\.join\(\"\\n\"\);",
            self.source,
            flags=re.DOTALL,
        )

        self.assertIsNotNone(match)
        body = match.group("body")

        self.assertIn('"1. prezzo sopra SMA200;"', body)
        self.assertIn('"2. RSI uguale o maggiore di 40;"', body)
        self.assertIn('"3. prezzo sopra quello di 7 giorni prima;"', body)
        self.assertIn('"4. volume BTC-USD sopra media 20 giorni."', body)
        self.assertNotIn('"5.', body)

    def test_live_conditions_use_red_and_green_icons(self) -> None:
        self.assertIn('condition.passed ? "✅" : "🅾️"', self.source)
        self.assertNotIn('condition.passed ? "OK" : "NO"', self.source)


if __name__ == "__main__":
    unittest.main()
