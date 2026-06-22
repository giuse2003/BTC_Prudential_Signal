from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from hourly_monitor import should_send_live_alert
from state.state_store import MonitorState


class LiveAlertTests(unittest.TestCase):
    def test_first_live_conditions_save_baseline_without_notification(self) -> None:
        state = MonitorState()

        must_notify, reason = should_send_live_alert(
            state,
            "BUY:00000|SELL:1",
            datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc),
        )

        self.assertFalse(must_notify)
        self.assertEqual(reason, "baseline LIVE salvata senza notifica")
        self.assertEqual(state.last_live_conditions_key, "BUY:00000|SELL:1")

    def test_live_condition_change_must_stay_stable_before_notification(self) -> None:
        now = datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
        state = MonitorState(last_live_conditions_key="BUY:00000|SELL:0")

        must_notify, _ = should_send_live_alert(state, "BUY:00000|SELL:1", now)
        self.assertFalse(must_notify)

        must_notify, reason = should_send_live_alert(
            state,
            "BUY:00000|SELL:1",
            now + timedelta(minutes=30),
        )

        self.assertTrue(must_notify)
        self.assertEqual(reason, "condizioni LIVE variate e stabili da almeno 30 minuti")

    def test_live_alert_cooldown_blocks_same_alert_for_two_hours(self) -> None:
        now = datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc)
        key = "BUY:00000|SELL:1"
        state = MonitorState(
            last_live_conditions_key=key,
            live_pending_conditions_key=key,
            live_pending_since_utc=(now - timedelta(minutes=45)).isoformat(),
            last_live_alert_conditions_key=key,
            last_live_alert_sent_at_utc=(now - timedelta(hours=1)).isoformat(),
        )

        must_notify, reason = should_send_live_alert(state, key, now)

        self.assertFalse(must_notify)
        self.assertEqual(reason, "allerta LIVE identica gia inviata nelle ultime 2 ore")


if __name__ == "__main__":
    unittest.main()
