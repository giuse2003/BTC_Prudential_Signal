from __future__ import annotations

import unittest
from pathlib import Path

from tools.verify_manifests import GIT_ROOT, MEGA_ROOT, verify_data_manifest, verify_source_manifest


class ManifestIntegrityTests(unittest.TestCase):
    def test_git_source_manifest_has_zero_errors(self) -> None:
        manifest_md = GIT_ROOT / "docs" / "BTC_SOURCE_MANIFEST.md"
        self.assertTrue(manifest_md.exists(), f"File mancante: {manifest_md}")
        ok, errors = verify_source_manifest()
        self.assertGreater(ok, 0, "Nessun sorgente verificato nel manifest.")
        self.assertEqual(errors, 0, f"Rilevati {errors} errori nel manifesto sorgenti.")

    def test_mega_data_manifest_has_zero_errors(self) -> None:
        csv_path = GIT_ROOT / "manifests" / "DATA_MANIFEST.csv"
        self.assertTrue(csv_path.exists(), f"File mancante: {csv_path}")
        if MEGA_ROOT.exists():
            ok, errors = verify_data_manifest()
            self.assertGreater(ok, 0, "Nessun dataset verificato su MEGA CLOUD.")
            self.assertEqual(errors, 0, f"Rilevati {errors} errori nel manifesto dati MEGA.")


if __name__ == "__main__":
    unittest.main()
