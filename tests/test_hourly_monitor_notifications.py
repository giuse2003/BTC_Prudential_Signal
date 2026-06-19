from __future__ import annotations

import unittest

from hourly_monitor import should_notify
from state.state_store import MonitorState


class HourlyMonitorNotificationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
