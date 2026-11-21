# -*- coding: utf-8 -*-
"""Verificatore di Integrita Crittografica per BTC-USD Signal.
Verifica gli hash SHA-256 esatti al byte registrati in:
1. docs/BTC_SOURCE_MANIFEST.md (Sorgenti del repository Git)
2. manifests/DATA_MANIFEST.csv (Artefatti pesanti e archivi su MEGA CLOUD)
"""

import csv
import hashlib
import re
import sys
from pathlib import Path

GIT_ROOT = Path(__file__).resolve().parents[1]
MEGA_ROOT = Path(r"D:\MEGA CLOUD\Trading\BTC SIGNAL")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source_manifest() -> tuple[int, int]:
    manifest_md = GIT_ROOT / "docs" / "BTC_SOURCE_MANIFEST.md"
    if not manifest_md.exists():
        print(f"[FAIL] File mancante: {manifest_md}")
        return 0, 1

    ok = 0
    errors = 0
    # Match righe tabella: | `file` | ruolo | bytes | `sha256` | `path` | stato |
    row_re = re.compile(
        r"^\|\s*`([^`]+)`\s*\|[^|]+\|[^|]+\|\s*`([0-9a-fA-F]{64})`\s*\|\s*`([^`]+)`\s*\|"
    )
    for line in manifest_md.read_text(encoding="utf-8").splitlines():
        m = row_re.match(line.strip())
        if not m:
            continue
        _, expected_sha, rel_path = m.groups()
        target = GIT_ROOT / Path(rel_path.replace("/", "\\"))
        if not target.exists():
            print(f"[MISSING SRC] {rel_path}")
            errors += 1
            continue
        actual_sha = sha256_file(target)
        if actual_sha.lower() != expected_sha.lower():
            print(
                f"[HASH MISMATCH SRC] {rel_path}: atteso {expected_sha}, calcolato {actual_sha}"
            )
            errors += 1
        else:
            ok += 1
    return ok, errors


def verify_data_manifest() -> tuple[int, int]:
    csv_path = GIT_ROOT / "manifests" / "DATA_MANIFEST.csv"
    if not csv_path.exists():
        print(f"[FAIL] File mancante: {csv_path}")
        return 0, 1

    ok = 0
    errors = 0
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rel_mega = row["relative_mega_path"]
            expected_sha = row["sha256"]
            expected_sz = int(row["size_bytes"])
            target = MEGA_ROOT / Path(rel_mega.replace("/", "\\"))
            if not target.exists():
                print(f"[MISSING MEGA] {rel_mega}")
                errors += 1
                continue
            actual_sz = target.stat().st_size
            actual_sha = sha256_file(target)
            if actual_sz != expected_sz or actual_sha.lower() != expected_sha.lower():
                print(
                    f"[MISMATCH MEGA] {rel_mega}: atteso ({expected_sz}, {expected_sha}), calcolato ({actual_sz}, {actual_sha})"
                )
                errors += 1
            else:
                ok += 1
    return ok, errors


def main() -> int:
    print(f"=== BTC-USD Signal Manifest Verification ===")
    print(f"Git Root:  {GIT_ROOT}")
    print(f"Mega Root: {MEGA_ROOT}")

    print("\n--- 1. Verifica docs/BTC_SOURCE_MANIFEST.md ---")
    src_ok, src_err = verify_source_manifest()
    print(f"Sorgenti Git verificati: {src_ok} OK, {src_err} errori")

    print("\n--- 2. Verifica manifests/DATA_MANIFEST.csv ---")
    if not MEGA_ROOT.exists():
        print(f"[AVVISO] Directory MEGA CLOUD non presente su questa macchina: {MEGA_ROOT}")
        mega_ok, mega_err = 0, 0
    else:
        mega_ok, mega_err = verify_data_manifest()
        print(f"Dataset MEGA CLOUD verificati: {mega_ok} OK, {mega_err} errori")

    total_errors = src_err + mega_err
    if total_errors == 0:
        print("\n[ALL PASS] Tutti i sorgenti e i dataset MEGA CLOUD sono verificati crittograficamente.")
        return 0
    else:
        print(f"\n[FAIL] Rilevati {total_errors} errori di integrita crittografica.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
