"""Valutazione riproducibile dei candidati V1-S1 e V1-B1."""

from __future__ import annotations

import json
import math
import platform
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from backtest.backtest import run_backtest
from config import CFG
from indicators.technical_indicators import compute_all_indicators
from pipeline import evaluation_frame
from reports.generate import save_dataframe_csv, write_utf8_text
from reproducibility import (
    dependency_versions,
    sha256_file,
    sha256_source_file,
)
from strategy.rules import ACTION_BUY, ACTION_HOLD, ACTION_SELL
from strategy.signals import compute_signals

AS_OF = "2026-07-26"
PRIMARY_COST = 0.006
COST_RATES = (0.0, 0.001, 0.0025, 0.004, PRIMARY_COST)
BOOTSTRAP_SEED = 20260727
BOOTSTRAP_SAMPLES = 5_000
BOOTSTRAP_BLOCK_DAYS = 30
FOLDS = (
    ("2017-2018", "2017-01-01", "2018-12-31"),
    ("2019-2020", "2019-01-01", "2020-12-31"),
    ("2021-2022", "2021-01-01", "2022-12-31"),
    ("2023-2024", "2023-01-01", "2024-12-31"),
    ("2025-2026", "2025-01-01", AS_OF),
)
EXPERIMENT_SOURCE_FILES = (
    "config.py",
    "indicators/technical_indicators.py",
    "experiments/candidate_evaluation.py",
    "run_candidate_experiment.py",
    "reproduce_candidate_experiment.py",
)
CANONICAL_ARTIFACTS = (
    "full_results.csv",
    "fold_results.csv",
    "bootstrap_results.csv",
    "decisions.json",
    "report.md",
)


@dataclass(frozen=True)
class Variant:
    key: str
    label: str
    use_volume: bool
    sell_days: int


VARIANTS = (
    Variant("BASELINE", "Baseline v1", True, 2),
    Variant("V1-S1", "Vendita dopo 1 Close sotto SMA50", True, 1),
    Variant("V1-B1", "Acquisto senza condizione volume", False, 2),
)


@dataclass(frozen=True)
class ExperimentResult:
    full_results: pd.DataFrame
    fold_results: pd.DataFrame
    bootstrap_results: pd.DataFrame
    decisions: dict
    periods: dict


def prepare_market(candles: pd.DataFrame) -> pd.DataFrame:
    frame = candles.copy().sort_index()
    frame.index = pd.DatetimeIndex(frame.index).tz_localize(None)
    return compute_all_indicators(frame)


def build_signals(frame: pd.DataFrame, variant: Variant) -> pd.Series:
    momentum_column = f"Close_{CFG.momentum_days}d_ago"
    buy = (
        (frame["Close"] > frame["SMA200"])
        & (frame["RSI"] >= 40)
        & (frame["Close"] > frame[momentum_column])
    )
    if variant.use_volume:
        buy &= frame["Volume"] > frame["VolumeAvg20"]

    below_sma50 = frame["Close"] < frame["SMA50"]
    sell = below_sma50.copy()
    for lag in range(1, variant.sell_days):
        sell &= below_sma50.shift(lag, fill_value=False)

    signals = pd.Series(ACTION_HOLD, index=frame.index, dtype=object)
    signals.loc[buy] = ACTION_BUY
    signals.loc[sell] = ACTION_SELL
    return signals


def strategy_path(
    frame: pd.DataFrame,
    signals: pd.Series,
    cost_per_side: float,
) -> pd.DataFrame:
    exposure_map = {ACTION_BUY: 1.0, ACTION_SELL: 0.0}
    desired = signals.map(exposure_map).astype(float).ffill().fillna(0.0)
    effective = desired.shift(1).fillna(0.0)
    market_return = frame["Close"].pct_change()
    gross_return = effective * market_return
    turnover = effective.diff().abs().fillna(effective.abs())

    net_return = (1.0 + gross_return.fillna(0.0)) * (
        1.0 - turnover * float(cost_per_side)
    ) - 1.0
    first_without_trade = market_return.isna() & turnover.eq(0.0)
    net_return.loc[first_without_trade] = np.nan
    equity = (1.0 + net_return.fillna(0.0)).cumprod()

    return pd.DataFrame(
        {
            "Close": frame["Close"],
            "Signal": signals,
            "DesiredExposure": desired,
            "EffectiveExposure": effective,
            "MarketReturn": market_return,
            "GrossReturn": gross_return,
            "TurnoverSides": turnover,
            "NetReturn": net_return,
            "Equity": equity,
        },
        index=frame.index,
    )


def _completed_trade_returns(path: pd.DataFrame) -> list[float]:
    active = path["EffectiveExposure"].gt(0.0).to_numpy()
    returns = path["NetReturn"].fillna(0.0)
    trade_returns: list[float] = []
    start: int | None = None

    for position, is_active in enumerate(active):
        if is_active and start is None:
            start = position
        elif not is_active and start is not None:
            trade_slice = returns.iloc[start : position + 1]
            trade_returns.append(float((1.0 + trade_slice).prod() - 1.0))
            start = None
    return trade_returns


def _metrics_from_returns(
    returns: pd.Series,
    *,
    annualization_periods: int,
) -> dict[str, float]:
    clean = returns.fillna(0.0)
    equity = (1.0 + clean).cumprod()
    final_growth = float(equity.iloc[-1])
    total_return = final_growth - 1.0
    periods = max(int(annualization_periods), 1)
    annualized = float(final_growth ** (365 / periods) - 1.0)
    running_max = np.maximum.accumulate(np.concatenate(([1.0], equity.to_numpy())))
    drawdown = float((equity.to_numpy() / running_max[1:] - 1.0).min())
    observed = returns.dropna()
    std = observed.std(ddof=1)
    sharpe = float(np.sqrt(365) * observed.mean() / std) if std else float("nan")
    return {
        "total_return": total_return,
        "annualized_return": annualized,
        "max_drawdown": drawdown,
        "sharpe_ratio": sharpe,
    }


def full_path_metrics(path: pd.DataFrame) -> dict[str, float | int]:
    result = _metrics_from_returns(
        path["NetReturn"],
        annualization_periods=max(len(path) - 1, 1),
    )
    trades = _completed_trade_returns(path)
    result.update(
        {
            "num_operations": len(trades),
            "win_rate": sum(value > 0.0 for value in trades) / len(trades) if trades else 0.0,
            "time_in_market": float(path["EffectiveExposure"].mean()),
            "turnover_sides": float(path["TurnoverSides"].sum()),
        }
    )
    return result


def _assert_matches_official_backtest(
    indicators: pd.DataFrame,
    signals: pd.Series,
    metrics: dict,
) -> None:
    official_frame = evaluation_frame(compute_signals(indicators))
    official_signals = official_frame["Segnale"]
    differences = signals.ne(official_signals)
    if differences.any():
        first = differences[differences].index[0].strftime("%Y-%m-%d")
        raise RuntimeError(
            f"La baseline sperimentale diverge dai segnali ufficiali dal {first}."
        )
    _, official, _ = run_backtest(
        official_frame[["Close", "Segnale"]]
    )
    checks = {
        "total_return": official.total_return,
        "annualized_return": official.annualized_return,
        "max_drawdown": official.max_drawdown,
        "sharpe_ratio": official.sharpe_ratio,
        "num_operations": official.num_operations,
        "win_rate": official.win_rate,
    }
    for name, expected in checks.items():
        if not math.isclose(float(metrics[name]), float(expected), rel_tol=1e-12, abs_tol=1e-12):
            raise RuntimeError(
                f"La baseline sperimentale diverge dal backtest ufficiale per {name}: "
                f"{metrics[name]} != {expected}"
            )


def _period_payload(candles: pd.DataFrame, evaluated: pd.DataFrame) -> dict:
    return {
        "history_start": candles.index[0].strftime("%Y-%m-%d"),
        "history_end": candles.index[-1].strftime("%Y-%m-%d"),
        "history_observations": int(len(candles)),
        "warmup_end": (evaluated.index[0] - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        "evaluation_start": evaluated.index[0].strftime("%Y-%m-%d"),
        "evaluation_end": evaluated.index[-1].strftime("%Y-%m-%d"),
        "evaluation_observations": int(len(evaluated)),
    }


def _moving_block_bootstrap(
    difference: pd.Series,
    *,
    samples: int = BOOTSTRAP_SAMPLES,
    block_days: int = BOOTSTRAP_BLOCK_DAYS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, float | int]:
    values = difference.fillna(0.0).to_numpy(dtype=float)
    n_observations = len(values)
    if n_observations < block_days:
        raise ValueError("Serie troppo corta per il moving-block bootstrap.")

    rng = np.random.default_rng(seed)
    blocks_per_sample = math.ceil(n_observations / block_days)
    max_start = n_observations - block_days
    annualized_means = np.empty(samples, dtype=float)
    offsets = np.arange(block_days)

    for sample in range(samples):
        starts = rng.integers(0, max_start + 1, size=blocks_per_sample)
        indices = (starts[:, None] + offsets[None, :]).reshape(-1)[:n_observations]
        annualized_means[sample] = values[indices].mean() * 365

    return {
        "observed_annualized_mean_difference": float(values.mean() * 365),
        "ci90_low": float(np.quantile(annualized_means, 0.05)),
        "ci90_high": float(np.quantile(annualized_means, 0.95)),
        "probability_positive": float(np.mean(annualized_means > 0.0)),
        "samples": samples,
        "block_days": block_days,
        "seed": seed,
    }


def evaluate_candidates(
    btc_candles: pd.DataFrame,
) -> ExperimentResult:
    full_rows: list[dict] = []
    fold_rows: list[dict] = []
    bootstrap_rows: list[dict] = []
    primary_paths: dict[str, pd.DataFrame] = {}

    indicators = prepare_market(btc_candles)
    frame = evaluation_frame(indicators)
    periods = {"BTC-USD": _period_payload(btc_candles, frame)}
    for variant in VARIANTS:
        signals = build_signals(indicators, variant).loc[frame.index]
        for cost in COST_RATES:
            path = strategy_path(frame, signals, cost)
            metrics = full_path_metrics(path)
            if variant.key == "BASELINE" and cost == 0.0:
                _assert_matches_official_backtest(indicators, signals, metrics)
            full_rows.append(
                {
                    "asset": "BTC-USD",
                    "variant": variant.key,
                    "label": variant.label,
                    "cost_per_side": cost,
                    **metrics,
                }
            )
            if cost == PRIMARY_COST:
                primary_paths[variant.key] = path

    for variant in VARIANTS:
        path = primary_paths[variant.key]
        for fold, start, end in FOLDS:
            segment = path.loc[start:end]
            if segment.empty:
                raise RuntimeError(f"Fold BTC-USD {fold} vuoto.")
            metrics = _metrics_from_returns(
                segment["NetReturn"],
                annualization_periods=len(segment),
            )
            fold_rows.append(
                {
                    "asset": "BTC-USD",
                    "fold": fold,
                    "start": segment.index[0].strftime("%Y-%m-%d"),
                    "end": segment.index[-1].strftime("%Y-%m-%d"),
                    "variant": variant.key,
                    "cost_per_side": PRIMARY_COST,
                    **metrics,
                    "turnover_sides": float(segment["TurnoverSides"].sum()),
                }
            )

    baseline_returns = primary_paths["BASELINE"]["NetReturn"]
    for variant in VARIANTS[1:]:
        candidate_returns = primary_paths[variant.key]["NetReturn"]
        bootstrap_rows.append(
            {
                "asset": "BTC-USD",
                "variant": variant.key,
                "cost_per_side": PRIMARY_COST,
                **_moving_block_bootstrap(candidate_returns - baseline_returns),
            }
        )

    full = pd.DataFrame(full_rows).sort_values(
        ["asset", "cost_per_side", "variant"]
    ).reset_index(drop=True)
    folds = pd.DataFrame(fold_rows).sort_values(
        ["asset", "fold", "variant"]
    ).reset_index(drop=True)
    bootstrap = pd.DataFrame(bootstrap_rows).sort_values(
        ["asset", "variant"]
    ).reset_index(drop=True)
    decisions = promotion_decisions(full, folds, bootstrap)
    return ExperimentResult(full, folds, bootstrap, decisions, periods)


def promotion_decisions(
    full: pd.DataFrame,
    folds: pd.DataFrame,
    bootstrap: pd.DataFrame,
) -> dict:
    primary = full.loc[np.isclose(full["cost_per_side"], PRIMARY_COST)]
    decisions: dict[str, dict] = {}

    for variant in (item.key for item in VARIANTS[1:]):
        baseline = primary.loc[primary["variant"] == "BASELINE"].iloc[0]
        candidate = primary.loc[primary["variant"] == variant].iloc[0]
        metric_checks = {
            "sharpe_improves": bool(candidate["sharpe_ratio"] > baseline["sharpe_ratio"]),
            "drawdown_within_2pp": bool(
                candidate["max_drawdown"] >= baseline["max_drawdown"] - 0.02
            ),
            "annualized_return_within_5pp": bool(
                candidate["annualized_return"] >= baseline["annualized_return"] - 0.05
            ),
            "turnover_increase_within_50pct": bool(
                candidate["turnover_sides"] <= baseline["turnover_sides"] * 1.5
            ),
        }

        fold_wins = 0
        fold_comparisons = 0
        for fold, _, _ in FOLDS:
            fold_baseline = folds.loc[
                (folds["fold"] == fold) & (folds["variant"] == "BASELINE")
            ].iloc[0]
            fold_candidate = folds.loc[
                (folds["fold"] == fold) & (folds["variant"] == variant)
            ].iloc[0]
            fold_comparisons += 1
            fold_wins += int(
                fold_candidate["sharpe_ratio"] > fold_baseline["sharpe_ratio"]
            )

        bootstrap_probability = float(
            bootstrap.loc[
                bootstrap["variant"] == variant,
                "probability_positive",
            ].iloc[0]
        )
        criteria = {
            **metric_checks,
            "at_least_3_of_5_fold_sharpe_wins": fold_wins >= 3,
            "bootstrap_probability_at_least_90pct": bootstrap_probability >= 0.90,
        }
        decisions[variant] = {
            "status": "PROMUOVIBILE" if all(criteria.values()) else "NON PROMUOVIBILE",
            "criteria": criteria,
            "fold_sharpe_wins": fold_wins,
            "fold_comparisons": fold_comparisons,
            "bootstrap_probability_positive": bootstrap_probability,
        }
    return decisions


def _git_commit(project_root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _pct(value: float) -> str:
    return f"{value * 100:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def _decimal(value: float) -> str:
    return f"{value:.3f}".replace(".", ",")


def _markdown_report(result: ExperimentResult, source_commit: str | None) -> str:
    primary = result.full_results.loc[
        np.isclose(result.full_results["cost_per_side"], PRIMARY_COST)
    ]
    lines = [
        "# Valutazione candidati BTC-USD Signal",
        "",
        f"Cutoff comune: `{AS_OF}`. Costo primario: `{PRIMARY_COST * 100:.2f}%` per lato.",
        f"Commit sorgente: `{source_commit or 'non disponibile'}`.",
        "",
        "La baseline operativa non e stata modificata. I candidati sono valutati secondo",
        "`MODEL_CANDIDATE_PROTOCOL.md` e usano esclusivamente BTC-USD.",
        "",
        "## Decisione",
        "",
        "| Candidato | Esito | Fold Sharpe vinti | Probabilita bootstrap |",
        "|---|---|---:|---:|",
    ]
    for variant, decision in result.decisions.items():
        lines.append(
            f"| {variant} | {decision['status']} | "
            f"{decision['fold_sharpe_wins']}/{decision['fold_comparisons']} | "
            f"{_pct(decision['bootstrap_probability_positive'])} |"
        )

    lines.extend(
        [
            "",
            "## Risultati al costo primario",
            "",
            "| Asset | Variante | Rendimento | Annualizzato | Drawdown | Sharpe | Operazioni | Lati |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in primary.itertuples(index=False):
        lines.append(
            f"| {row.asset} | {row.variant} | {_pct(row.total_return)} | "
            f"{_pct(row.annualized_return)} | {_pct(row.max_drawdown)} | "
            f"{_decimal(row.sharpe_ratio)} | {row.num_operations} | "
            f"{int(row.turnover_sides)} |"
        )

    lines.extend(["", "## Criteri", ""])
    for variant, decision in result.decisions.items():
        lines.append(f"### {variant}: {decision['status']}")
        lines.append("")
        for criterion, passed in decision["criteria"].items():
            lines.append(f"- [{'x' if passed else ' '}] `{criterion}`")
        lines.append("")

    lines.extend(
        [
            "## Periodi",
            "",
            "| Asset | Storico | Valutazione | Osservazioni valutate |",
            "|---|---|---|---:|",
        ]
    )
    for asset, period in result.periods.items():
        lines.append(
            f"| {asset} | {period['history_start']} / {period['history_end']} | "
            f"{period['evaluation_start']} / {period['evaluation_end']} | "
            f"{period['evaluation_observations']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretazione corretta",
            "",
            "I candidati sono stati scelti dopo aver osservato l'intero storico BTC. I risultati",
            "non sono quindi out-of-sample. I blocchi e il bootstrap misurano stabilita interna,",
            "ma non correggono interamente selection bias e cambi di regime. Nessun dato o",
            "progetto ETH-USD e stato usato in questa valutazione.",
            "",
            "Le commissioni Coinbase effettive dipendono da maker/taker e volume personale.",
            "Gli scenari sono stress test, non un preventivo di costo. Slippage, spread, imposte",
            "e rendimento della liquidita restano esclusi.",
            "",
            "Riferimenti:",
            "",
            "- https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees",
            "- https://papers.ssrn.com/sol3/Papers.cfm?abstract_id=2326253",
            "- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_outputs(
    result: ExperimentResult,
    target: Path,
    source_commit: str | None,
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    save_dataframe_csv(result.full_results, target / "full_results.csv", index=False)
    save_dataframe_csv(result.fold_results, target / "fold_results.csv", index=False)
    save_dataframe_csv(
        result.bootstrap_results,
        target / "bootstrap_results.csv",
        index=False,
    )
    write_utf8_text(
        target / "decisions.json",
        json.dumps(result.decisions, indent=2, allow_nan=False),
    )
    write_utf8_text(target / "report.md", _markdown_report(result, source_commit))


def create_experiment_run(
    btc_candles: pd.DataFrame,
    output_dir: str | Path,
    *,
    source_commit: str | None = None,
) -> Path:
    project_root = Path(__file__).resolve().parents[1]
    target = Path(output_dir)
    commit = source_commit if source_commit is not None else _git_commit(project_root)
    result = evaluate_candidates(btc_candles)
    _write_outputs(result, target, commit)

    artifacts = {
        name: {
            "path": name,
            "sha256": sha256_file(target / name),
            "bytes": (target / name).stat().st_size,
        }
        for name in CANONICAL_ARTIFACTS
    }
    lock_path = project_root / "requirements.lock"
    manifest = {
        "experiment_id": f"model-candidates-v1-{AS_OF}",
        "run_type": "research-only",
        "as_of": AS_OF,
        "baseline_unchanged": True,
        "protocol": "../../../MODEL_CANDIDATE_PROTOCOL.md",
        "source": {
            "commit": commit,
            "files": {
                name: sha256_source_file(project_root / name)
                for name in EXPERIMENT_SOURCE_FILES
            },
        },
        "environment": {
            "python": platform.python_version(),
            "dependencies": dependency_versions(),
            "requirements_lock_sha256": sha256_file(lock_path),
        },
        "inputs": {
            "BTC-USD": {
                "path": "../../runs/baseline-v1-2026-07-26/raw_candles.csv",
                "sha256": sha256_file(
                    project_root
                    / "docs/runs/baseline-v1-2026-07-26/raw_candles.csv"
                ),
            }
        },
        "parameters": {
            "variants": [variant.__dict__ for variant in VARIANTS],
            "cost_rates_per_side": list(COST_RATES),
            "primary_cost_per_side": PRIMARY_COST,
            "folds": [list(fold) for fold in FOLDS],
            "bootstrap": {
                "seed": BOOTSTRAP_SEED,
                "samples": BOOTSTRAP_SAMPLES,
                "block_days": BOOTSTRAP_BLOCK_DAYS,
                "confidence_interval": 0.90,
            },
        },
        "periods": result.periods,
        "decisions": result.decisions,
        "artifacts": artifacts,
    }
    manifest_path = target / "manifest.json"
    write_utf8_text(
        manifest_path,
        json.dumps(manifest, indent=2, allow_nan=False),
    )
    return manifest_path


def verify_experiment_run(
    manifest_path: str | Path,
    *,
    strict_environment: bool = True,
) -> dict:
    project_root = Path(__file__).resolve().parents[1]
    manifest_path = Path(manifest_path).resolve()
    run_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("run_type") != "research-only":
        raise ValueError("Il manifest non descrive l'esperimento candidati.")

    if strict_environment:
        if platform.python_version() != manifest["environment"]["python"]:
            raise RuntimeError("Versione Python diversa dall'esperimento.")
        if dependency_versions() != manifest["environment"]["dependencies"]:
            raise RuntimeError("Dipendenze diverse dall'esperimento.")
    if sha256_file(project_root / "requirements.lock") != manifest["environment"][
        "requirements_lock_sha256"
    ]:
        raise RuntimeError("requirements.lock diverso dall'esperimento.")
    for name, expected in manifest["source"]["files"].items():
        if sha256_source_file(project_root / name) != expected:
            raise RuntimeError(f"Sorgente esperimento modificato: {name}")
    for name, info in manifest["artifacts"].items():
        if sha256_file(run_dir / info["path"]) != info["sha256"]:
            raise RuntimeError(f"Artefatto esperimento non valido: {name}")

    btc_path = (run_dir / manifest["inputs"]["BTC-USD"]["path"]).resolve()
    if sha256_file(btc_path) != manifest["inputs"]["BTC-USD"]["sha256"]:
        raise RuntimeError("Snapshot BTC non valido.")
    btc = pd.read_csv(btc_path, parse_dates=["Date"], index_col="Date")

    with tempfile.TemporaryDirectory(prefix="btc-candidate-reproduce-") as temp_dir:
        generated = Path(temp_dir)
        result = evaluate_candidates(btc)
        _write_outputs(result, generated, manifest["source"]["commit"])
        for name in CANONICAL_ARTIFACTS:
            actual = sha256_file(generated / name)
            expected = manifest["artifacts"][name]["sha256"]
            if actual != expected:
                raise RuntimeError(
                    f"Riproduzione esperimento non identica per {name}: {actual} != {expected}"
                )
    return {
        "experiment_id": manifest["experiment_id"],
        "decisions": manifest["decisions"],
        "verified_artifacts": list(CANONICAL_ARTIFACTS),
    }
