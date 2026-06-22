from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from state.state_store import MonitorState, load_state, save_state


class StateStoreTests(unittest.TestCase):
    def test_round_trips_last_processed_candle_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "state.json"
            save_state(
                path,
                MonitorState(
                    last_signal="VENDI",
                    last_processed_candle_date="2026-06-21",
                ),
            )

            state = load_state(path)

        self.assertEqual(state.last_signal, "VENDI")
        self.assertEqual(state.last_processed_candle_date, "2026-06-21")


if __name__ == "__main__":
    unittest.main()
