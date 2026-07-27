from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reports.publication import validate_bundle, write_manifest


class PublicationBundleTests(unittest.TestCase):
    def test_rejects_mixed_run_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            for name in ("status.json", "live-status.json"):
                (root / name).write_text(json.dumps({"run_id": "run-a"}), encoding="utf-8")
            (root / "chart-data.json").write_text(
                json.dumps({"run_id": "run-b", "rows": []}), encoding="utf-8"
            )
            write_manifest(
                root,
                {"run_id": "run-a"},
                period={},
                metrics={},
                provenance={},
                artifact_names=["status.json", "live-status.json", "chart-data.json"],
            )
            with self.assertRaisesRegex(ValueError, "run_id incoerente"):
                validate_bundle(root)

    def test_accepts_complete_bundle_with_matching_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            for name in ("status.json", "live-status.json", "chart-data.json"):
                (root / name).write_text(json.dumps({"run_id": "run-a"}), encoding="utf-8")
            write_manifest(
                root,
                {"run_id": "run-a"},
                period={},
                metrics={},
                provenance={},
                artifact_names=["status.json", "live-status.json", "chart-data.json"],
            )
            validate_bundle(root)


if __name__ == "__main__":
    unittest.main()
