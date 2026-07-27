from __future__ import annotations

import unittest
from pathlib import Path

from experiments.candidate_evaluation import verify_experiment_run


class CandidateReproducibilityTests(unittest.TestCase):
    def test_btc_only_candidate_experiment_is_reproduced_exactly(self) -> None:
        root = Path(__file__).resolve().parents[1]
        manifest = (
            root
            / "docs/experiments/btc-model-candidates-v1-2026-07-26/manifest.json"
        )

        result = verify_experiment_run(manifest, strict_environment=True)

        self.assertEqual(result["experiment_id"], "model-candidates-v1-2026-07-26")
        self.assertEqual(result["decisions"]["V1-S1"]["status"], "NON PROMUOVIBILE")
        self.assertEqual(result["decisions"]["V1-B1"]["status"], "NON PROMUOVIBILE")
        self.assertEqual(len(result["verified_artifacts"]), 5)


if __name__ == "__main__":
    unittest.main()
