"""Pubblicazione validata e transazionale degli artefatti di un'esecuzione."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from config import CFG

PUBLIC_JSON_FILES = ("status.json", "live-status.json", "chart-data.json")


def new_run_metadata() -> dict[str, str]:
    return {
        "run_id": f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project": CFG.model_name,
        "model_version": CFG.model_version,
        "data_source": CFG.data_source,
        "market": CFG.product_id,
        "timezone": "UTC",
    }


@contextmanager
def staged_run(target_dir: str | Path) -> Iterator[Path]:
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="btc-usd-signal-") as temp_dir:
        yield Path(temp_dir)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(
    staging_dir: str | Path,
    metadata: dict,
    *,
    period: dict,
    metrics: dict,
    artifact_names: list[str],
) -> Path:
    staging = Path(staging_dir)
    artifacts = {
        name: {"sha256": _sha256(staging / name), "bytes": (staging / name).stat().st_size}
        for name in artifact_names
    }
    payload = {
        **metadata,
        "period": period,
        "rules": {
            "buy": [
                "Close > SMA200",
                "RSI14 >= 40",
                "Close > Close 7 giorni prima",
                "Volume BTC-USD > media 20 giorni",
            ],
            "sell": ["Close < SMA50 per due candele giornaliere consecutive"],
            "sell_precedence": True,
            "execution_delay_days": 1,
            "exposure": "0% o 100%; MANTIENI STATO ATTUALE conserva l'esposizione",
            "fees_and_slippage": "non inclusi",
        },
        "metrics": metrics,
        "artifacts": artifacts,
    }
    path = staging / "manifest.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def validate_bundle(staging_dir: str | Path) -> None:
    staging = Path(staging_dir)
    manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
    run_id = manifest.get("run_id")
    if not run_id:
        raise ValueError("Manifest senza run_id.")
    for name in PUBLIC_JSON_FILES:
        payload = json.loads((staging / name).read_text(encoding="utf-8"))
        if payload.get("run_id") != run_id:
            raise ValueError(f"run_id incoerente in {name}.")
    for name, info in manifest.get("artifacts", {}).items():
        path = staging / name
        if not path.exists() or _sha256(path) != info.get("sha256"):
            raise ValueError(f"Artefatto non valido: {name}")


def publish_bundle(
    staging_dir: str | Path,
    target_dir: str | Path,
    artifact_names: list[str],
) -> None:
    """Promuove tutti i file e ripristina la versione precedente su errore."""
    staging = Path(staging_dir)
    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    names = [*artifact_names, "manifest.json"]
    backup_dir = Path(tempfile.mkdtemp(prefix="btc-usd-signal-backup-"))
    replaced: list[str] = []
    try:
        for name in names:
            destination = target / name
            if destination.exists():
                shutil.copy2(destination, backup_dir / name)
        for name in names:
            source = staging / name
            if not source.exists():
                raise FileNotFoundError(source)
            temporary = target / f".{name}.new"
            shutil.copy2(source, temporary)
            os.replace(temporary, target / name)
            replaced.append(name)
    except Exception:
        for name in replaced:
            backup = backup_dir / name
            destination = target / name
            if backup.exists():
                os.replace(backup, destination)
            elif destination.exists():
                destination.unlink()
        raise
    finally:
        shutil.rmtree(backup_dir, ignore_errors=True)
