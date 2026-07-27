"""Verifica offline e byte per byte l'esperimento sui candidati."""

from __future__ import annotations

import argparse
import json

from experiments.candidate_evaluation import verify_experiment_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Riproduce l'esperimento candidati.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--allow-environment-drift", action="store_true")
    args = parser.parse_args()
    result = verify_experiment_run(
        args.manifest,
        strict_environment=not args.allow_environment_drift,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
