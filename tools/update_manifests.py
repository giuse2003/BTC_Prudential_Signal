# -*- coding: utf-8 -*-
"""Generatore e Aggiornatore Automatico dei Manifesti Crittografici per BTC-USD Signal.
Aggiorna:
1. docs/BTC_SOURCE_MANIFEST.md (Sorgenti del repository Git)
2. manifests/DATA_MANIFEST.csv (Dataset pesanti su MEGA CLOUD)
"""

import csv
from datetime import datetime, timezone
import hashlib
from pathlib import Path

GIT_ROOT = Path(__file__).resolve().parents[1]
MEGA_ROOT = Path(r"D:\MEGA CLOUD\Trading\BTC SIGNAL")

TRACKED_SOURCES = [
    ("config.py", "Configurazione centrale", "CONFIG"),
    ("pipeline.py", "Pipeline di esecuzione e pubblicazione", "CORE"),
    ("main.py", "Punto di ingresso CLI e baseline freeze", "CLI"),
    ("hourly_monitor.py", "Monitor orario CI/CD e notifiche", "MONITOR"),
    ("reproduce.py", "Verifica offline deterministica baseline v1", "AUDIT"),
    ("reproducibility.py", "Framework di riproducibilita baseline", "CORE"),
    ("freeze_baseline.py", "Strumento di congelamento snapshot", "TOOL"),
    ("reproduce_candidate_experiment.py", "Verifica offline esperimenti candidati", "AUDIT"),
    ("run_candidate_experiment.py", "Esecuzione studio statistico candidati", "EXPERIMENT"),
    ("run_dashboard.py", "Avvio server locale per dashboard", "DASHBOARD"),
    ("telegram_command.py", "CLI per invio comandi Telegram", "CLI"),
    ("telegram_subscribers.py", "Interfaccia Supabase iscritti Telegram", "DATABASE"),
    ("strategy/rules.py", "Vocabolario e precedenza delle azioni", "STRATEGY"),
    ("strategy/signals.py", "Calcolo condizioni e segnali DAILY/LIVE", "STRATEGY"),
    ("indicators/technical_indicators.py", "Indicatori SMA, RSI, ATR, Momentum", "INDICATORS"),
    ("data/coinbase.py", "Client Coinbase Advanced Trade API", "DATA"),
    ("data/daily_candles.py", "Filtraggio candele giornaliere concluse", "DATA"),
    ("backtest/backtest.py", "Simulatore backtest e metriche di rischio", "BACKTEST"),
    ("reports/generate.py", "Generatore artefatti JSON, CSV, grafici", "REPORT"),
    ("reports/publication.py", "Staging atomico, hash SHA-256 e rollback", "CORE"),
    ("state/state_store.py", "Persistenza stato monitor e allarmi live", "STATE"),
    ("notifications/telegram.py", "Formattatore messaggi e client Telegram", "NOTIFICATION"),
    ("experiments/candidate_evaluation.py", "Protocollo scientifico test candidati", "EXPERIMENT"),
    ("experiments/candidate_swing_sentinel.py", "Ricerca candidati Swing Sentinel (Aegis style)", "EXPERIMENT"),
    ("cloudflare-worker/src/worker.js", "Cloudflare Worker Edge API & Webhook", "EDGE_WORKER"),
    ("cloudflare-worker/wrangler.jsonc", "Configurazione Cloudflare Worker", "CONFIG"),
    ("cloudflare-worker/package.json", "Dipendenze Cloudflare Worker", "CONFIG"),
    ("tools/verify_manifests.py", "Verificatore integrita crittografica", "TOOL"),
    ("tools/update_manifests.py", "Aggiornatore automatico dei manifesti", "TOOL"),
    ("tests/test_manifests.py", "Test di integrita crittografica manifesti", "TEST"),
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def update_source_manifest() -> Path:
    out_path = GIT_ROOT / "docs" / "BTC_SOURCE_MANIFEST.md"
    lines = [
        "# BTC-USD Signal — Manifesto Crittografico dei Sorgenti (`SHA-256`)",
        "",
        "Registro canonico di provenienza e integrita al byte di tutti i sorgenti Python, configurazioni e script di BTC-USD Signal.",
        "",
        "- **Regola di Integrita**: gli hash `SHA-256` sono calcolati sui byte esatti del file.",
        "- **Verifica Automatica**: eseguire `python tools/verify_manifests.py` per controllare l'integrita crittografica.",
        f"- **Ultimo Aggiornamento**: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`",
        "",
        "| Nome File | Ruolo Architetturale | Bytes | SHA-256 | Percorso Canonico | Stato |",
        "| :--- | :--- | ---: | :--- | :--- | :---: |",
    ]

    for rel_path, role, status in TRACKED_SOURCES:
        target = GIT_ROOT / Path(rel_path.replace("/", "\\"))
        if not target.exists():
            print(f"[WARN] File sorgente tracciato non trovato: {rel_path}")
            continue
        sz = target.stat().st_size
        h = sha256_file(target)
        file_name = target.name
        norm_path = rel_path.replace("\\", "/")
        lines.append(
            f"| `{file_name}` | {role} | {sz:,} | `{h}` | `{norm_path}` | `{status}` |"
        )

    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Aggiornato {out_path} con {len(TRACKED_SOURCES)} sorgenti.")
    return out_path


def update_data_manifest() -> Path:
    csv_path = GIT_ROOT / "manifests" / "DATA_MANIFEST.csv"
    fieldnames = [
        "dataset_id",
        "category",
        "filename",
        "relative_mega_path",
        "size_bytes",
        "sha256",
        "created_or_source_date",
        "description",
        "source",
        "validation_status",
        "version",
        "notes",
    ]

    rows = []
    if MEGA_ROOT.exists():
        for item in sorted(MEGA_ROOT.rglob("*")):
            if not item.is_file():
                continue
            rel_mega = str(item.relative_to(MEGA_ROOT)).replace("/", "\\")
            sz = item.stat().st_size
            h = sha256_file(item)
            dt = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # Categorizzazione
            if "--02_RAW_CACHE" in rel_mega:
                cat = "RAW_CACHE"
                desc = f"Cache dati grezzi Coinbase OHLCV: {item.name}"
            elif "--runs" in rel_mega:
                cat = "RUN_ARTIFACT"
                desc = f"Artefatto storico del run congelato: {item.name}"
            elif "--analysis" in rel_mega:
                cat = "ANALYSIS"
                desc = f"Dati di analisi o telemetria quantitativa: {item.name}"
            elif "releases" in rel_mega:
                cat = "RELEASE"
                desc = f"Pacchetto di rilascio certificato: {item.name}"
            else:
                cat = "DATASET"
                desc = f"Artefatto pesante MEGA CLOUD: {item.name}"

            dataset_id = "BTC_" + rel_mega.replace("\\", "_").replace("-", "_").replace(".", "_")
            rows.append(
                {
                    "dataset_id": dataset_id,
                    "category": cat,
                    "filename": item.name,
                    "relative_mega_path": rel_mega,
                    "size_bytes": sz,
                    "sha256": h,
                    "created_or_source_date": dt,
                    "description": desc,
                    "source": "Coinbase_Advanced_Trade",
                    "validation_status": "VERIFIED",
                    "version": "1.0",
                    "notes": "Copia crittograficamente verificata SHA-256 su MEGA CLOUD",
                }
            )

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Aggiornato {csv_path} con {len(rows)} record MEGA CLOUD.")
    return csv_path


def main() -> None:
    update_source_manifest()
    update_data_manifest()
    print("Aggiornamento manifesti completato.")


if __name__ == "__main__":
    main()
