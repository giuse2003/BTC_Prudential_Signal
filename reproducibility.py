"""Creazione e verifica offline dei baseline congelati."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from backtest.backtest import BacktestMetrics, run_backtest
from config import CFG
from indicators.technical_indicators import compute_all_indicators
from pipeline import evaluation_frame
from reports.generate import (
    save_chart_data_json,
    save_dataframe_csv,
    save_historical_csv,
    save_status_json,
    save_text_report,
)
from strategy.signals import compute_signals

FROZEN_ARTIFACTS = (
    "raw_candles.csv",
    "status.json",
    "chart-data.json",
    "historical_signals.csv",
    "equity_timeseries.csv",
    "report.txt",
)
GENERATED_ARTIFACTS = tuple(name for name in FROZEN_ARTIFACTS if name != "raw_candles.csv")
MODEL_SOURCE_FILES = (
    "config.py",
    "backtest/backtest.py",
    "data/coinbase.py",
    "indicators/technical_indicators.py",
    "pipeline.py",
    "reports/generate.py",
    "reproducibility.py",
    "strategy/rules.py",
    "strategy/signals.py",
)
LOCKED_DISTRIBUTIONS = (
    "certifi",
    "charset-normalizer",
    "contourpy",
    "cycler",
    "fonttools",
    "idna",
    "kiwisolver",
    "packaging",
    "pillow",
    "pyparsing",
    "python-dateutil",
    "six",
    "tzdata",
    "urllib3",
    "numpy",
    "pandas",
    "matplotlib",
    "requests",
)


@dataclass(frozen=True)
class BaselineResult:
    signals: pd.DataFrame
    equity: pd.DataFrame
    strategy_metrics: BacktestMetrics
    buy_hold_metrics: BacktestMetrics
    period: dict


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_source_file(path: str | Path) -> str:
    normalized = Path(path).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(normalized).hexdigest()


def dependency_versions() -> dict[str, str]:
    return {
        name: importlib.metadata.version(name)
        for name in LOCKED_DISTRIBUTIONS
    }


def source_hashes(project_root: Path) -> dict[str, str]:
    return {name: sha256_source_file(project_root / name) for name in MODEL_SOURCE_FILES}


def compute_baseline(candles: pd.DataFrame, initial_capital: float = 1.0) -> BaselineResult:
    signals = evaluation_frame(compute_signals(compute_all_indicators(candles)))
    equity, strategy_metrics, buy_hold_metrics = run_backtest(
        signals[["Close", "Segnale"]],
        initial_capital=initial_capital,
    )
    period = {
        "coinbase_history_start": candles.index[0].strftime("%Y-%m-%d"),
        "warmup_end": (signals.index[0] - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        "evaluation_start": signals.index[0].strftime("%Y-%m-%d"),
        "evaluation_end": signals.index[-1].strftime("%Y-%m-%d"),
        "calendar_days": int((signals.index[-1] - signals.index[0]).days + 1),
        "observations": int(len(signals)),
    }
    return BaselineResult(signals, equity, strategy_metrics, buy_hold_metrics, period)


def _metrics(result: BaselineResult) -> dict:
    return {
        "strategy": asdict(result.strategy_metrics),
        "buy_and_hold": asdict(result.buy_hold_metrics),
    }


def _metadata(run_id: str, as_of: str) -> dict[str, str]:
    return {
        "run_id": run_id,
        "run_type": "frozen-baseline",
        "as_of": as_of,
        "project": CFG.model_name,
        "model_version": CFG.model_version,
        "data_source": CFG.data_source,
        "market": CFG.product_id,
        "timezone": "UTC",
    }


def _write_outputs(
    result: BaselineResult,
    target: Path,
    metadata: dict,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    save_status_json(result.signals, metadata=metadata, out_path=target / "status.json")
    save_chart_data_json(result.signals, target / "chart-data.json", metadata)
    save_historical_csv(result.signals, target / "historical_signals.csv")
    save_dataframe_csv(result.equity, target / "equity_timeseries.csv", index=True)
    save_text_report(
        result.signals,
        result.strategy_metrics,
        result.buy_hold_metrics,
        target / "report.txt",
    )


def _formulas() -> dict:
    return {
        "indicators": {
            "sma50_sma200": "rolling arithmetic mean; min_periods equals window",
            "rsi14": "delta; gains/losses clipped at zero; ewm alpha=1/14, adjust=false, min_periods=14",
            "volume_avg20": "rolling arithmetic mean; min_periods=20; Coinbase base volume in BTC",
            "atr14": "max(H-L, abs(H-prevClose), abs(L-prevClose)); ewm alpha=1/14, adjust=false, min_periods=14",
            "momentum7": "Close.shift(7)",
        },
        "actions": {
            "buy": "Close>SMA200 and RSI14>=40 and Close>Close.shift(7) and Volume>VolumeAvg20",
            "sell": "Close<SMA50 for the current and immediately previous daily candle",
            "precedence": "sell, then buy, otherwise MANTIENI STATO ATTUALE",
        },
        "backtest": {
            "desired_exposure": "ACQUISTA=1; VENDI=0; hold=forward-fill previous exposure; initial=0",
            "effective_exposure": "desired_exposure.shift(1); initial=0",
            "btc_return": "Close.pct_change()",
            "strategy_return": "effective_exposure * btc_return",
            "equity": "cumprod(1 + daily_return)",
            "buy_and_hold": "Close / first Close on the evaluation period",
            "annualized_return": "(final_equity/initial_equity) ** (365/(observations-1)) - 1",
            "max_drawdown": "min(equity/equity.cummax() - 1)",
            "sharpe": "sqrt(365) * mean(daily_return) / sample_std(daily_return, ddof=1); risk-free=0",
            "trades": "only completed 0-to-long-to-0 positions; open final position excluded",
            "fees_slippage_taxes": "excluded",
        },
    }


def create_frozen_run(
    candles: pd.DataFrame,
    *,
    as_of: str,
    output_dir: str | Path,
    run_id: str | None = None,
    source_tag: str | None = None,
    initial_capital: float = 1.0,
) -> Path:
    project_root = Path(__file__).resolve().parent
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    major_version = CFG.model_version.split(".", maxsplit=1)[0]
    run_id = run_id or f"baseline-v{major_version}-{as_of}"
    metadata = _metadata(run_id, as_of)

    raw = candles.loc[candles.index <= pd.Timestamp(as_of)].copy().sort_index()
    raw.index.name = "Date"
    save_dataframe_csv(raw, target / "raw_candles.csv", index=True)
    round_tripped = pd.read_csv(
        target / "raw_candles.csv",
        parse_dates=["Date"],
        index_col="Date",
    )
    result = compute_baseline(round_tripped, initial_capital=initial_capital)
    if result.period["evaluation_end"] != as_of:
        raise ValueError(
            f"Il baseline termina il {result.period['evaluation_end']}, non alla data richiesta {as_of}."
        )
    _write_outputs(result, target, metadata)

    lock_path = project_root / "requirements.lock"
    artifacts = {
        name: {
            "path": name,
            "sha256": sha256_file(target / name),
            "bytes": (target / name).stat().st_size,
        }
        for name in FROZEN_ARTIFACTS
    }
    manifest = {
        **metadata,
        "source": {
            "repository": "https://github.com/giuse2003/BTC_Prudential_Signal",
            "tag": source_tag,
            "identity": "Git tag plus SHA-256 hashes of model source files normalized to LF",
            "files": source_hashes(project_root),
        },
        "environment": {
            "python": platform.python_version(),
            "dependencies": dependency_versions(),
            "requirements_lock": "../../../requirements.lock",
            "requirements_lock_sha256": sha256_file(lock_path),
        },
        "input": {
            "snapshot": "raw_candles.csv",
            "snapshot_sha256": artifacts["raw_candles.csv"]["sha256"],
            "api_base_url": "https://api.coinbase.com/api/v3/brokerage/market",
            "endpoint": "/products/BTC-USD/candles",
            "granularity": "ONE_DAY",
            "requested_start": CFG.start_date,
            "inclusive_end": as_of,
            "cache_used_for_reproduction": False,
        },
        "period": result.period,
        "formulas": _formulas(),
        "metrics": _metrics(result),
        "artifacts": artifacts,
    }
    manifest_path = target / "manifest.json"
    manifest_path.write_bytes(json.dumps(manifest, indent=2).encode("utf-8"))
    return manifest_path


def _verify_environment(manifest: dict) -> None:
    expected = manifest["environment"]
    if platform.python_version() != expected["python"]:
        raise RuntimeError(
            f"Python {platform.python_version()} in uso; richiesto {expected['python']}."
        )
    installed = dependency_versions()
    if installed != expected["dependencies"]:
        raise RuntimeError(f"Dipendenze diverse dal baseline: {installed}")


def verify_frozen_run(
    manifest_path: str | Path,
    *,
    strict_environment: bool = True,
) -> dict:
    project_root = Path(__file__).resolve().parent
    manifest_path = Path(manifest_path).resolve()
    run_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("run_type") != "frozen-baseline":
        raise ValueError("Il manifest non descrive un baseline congelato.")

    if strict_environment:
        _verify_environment(manifest)
    lock_path = project_root / "requirements.lock"
    if sha256_file(lock_path) != manifest["environment"]["requirements_lock_sha256"]:
        raise RuntimeError("requirements.lock non coincide con il baseline.")
    for name, expected_hash in manifest["source"]["files"].items():
        if sha256_source_file(project_root / name) != expected_hash:
            raise RuntimeError(f"Sorgente modificato rispetto al baseline: {name}")
    for name, info in manifest["artifacts"].items():
        if sha256_file(run_dir / info["path"]) != info["sha256"]:
            raise RuntimeError(f"Artefatto pubblicato non valido: {name}")

    candles = pd.read_csv(
        run_dir / manifest["input"]["snapshot"],
        parse_dates=["Date"],
        index_col="Date",
    )
    result = compute_baseline(candles)
    metadata = _metadata(manifest["run_id"], manifest["as_of"])
    with tempfile.TemporaryDirectory(prefix="btc-usd-reproduce-") as temp_dir:
        generated = Path(temp_dir)
        _write_outputs(result, generated, metadata)
        for name in GENERATED_ARTIFACTS:
            actual = sha256_file(generated / name)
            expected = manifest["artifacts"][name]["sha256"]
            if actual != expected:
                raise RuntimeError(f"Riproduzione non identica per {name}: {actual} != {expected}")
    if _metrics(result) != manifest["metrics"]:
        raise RuntimeError("Le metriche ricalcolate non coincidono con il manifest.")
    return {
        "run_id": manifest["run_id"],
        "period": result.period,
        "metrics": _metrics(result),
        "verified_artifacts": list(FROZEN_ARTIFACTS),
    }
