from __future__ import annotations

import unittest
from pathlib import Path

from reproducibility import verify_frozen_run


class ReproducibilityTests(unittest.TestCase):
    def test_frozen_baseline_is_reproduced_exactly(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifest = root / "docs" / "runs" / "baseline-v1-2026-07-26" / "manifest.json"

        result = verify_frozen_run(manifest, strict_environment=True)

        self.assertEqual(result["run_id"], "baseline-v1-2026-07-26")
        self.assertEqual(result["period"]["evaluation_start"], "2016-02-04")
        self.assertEqual(result["period"]["evaluation_end"], "2026-07-26")
        self.assertEqual(result["period"]["observations"], 3826)
        self.assertAlmostEqual(
            result["metrics"]["strategy"]["total_return"],
            367.38206612273154,
        )
        self.assertAlmostEqual(
            result["metrics"]["buy_and_hold"]["total_return"],
            167.40916002989766,
        )


if __name__ == "__main__":
    unittest.main()
