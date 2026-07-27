"""Verifica offline un baseline congelato e tutti i suoi hash."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from reproducibility import verify_frozen_run


def main() -> None:
    parser = argparse.ArgumentParser(description="Riproduce e verifica BTC-USD Signal.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--allow-environment-drift",
        action="store_true",
        help="Ricalcola senza imporre le versioni bloccate; gli hash restano obbligatori.",
    )
    args = parser.parse_args()
    result = verify_frozen_run(
        args.manifest,
        strict_environment=not args.allow_environment_drift,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
