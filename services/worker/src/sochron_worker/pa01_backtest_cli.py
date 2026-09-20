"""Explicit offline PA01 replay operator; no default work or external connection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pa01_backtest import (
    PA01BacktestInvalid,
    build_bundle,
    load_backtest_input,
    write_bundle,
)
from .research_evaluation import evaluate_bundle


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise PA01BacktestInvalid()


def main(argv=None) -> int:
    try:
        parser = Parser(description="Offline Demo PA01 tick-replay bundle builder")
        parser.add_argument("action", choices=("build",))
        parser.add_argument("--input", required=True)
        parser.add_argument("--output", required=True)
        args = parser.parse_args(argv)
        source = load_backtest_input(Path(args.input))
        bundle = build_bundle(source)
        evaluation = evaluate_bundle(bundle)
        digest = write_bundle(Path(args.output), bundle)
        print(
            json.dumps(
                {
                    "state": "BUILT",
                    "dataset_hash": digest,
                    "evaluation_fingerprint": evaluation.evaluation_fingerprint,
                    "sample_size": evaluation.metrics.sample_size,
                    "promotion_decided": False,
                    "execution_ready": False,
                    "auto_trading_enabled": False,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 0
    except PA01BacktestInvalid as error:
        print(
            json.dumps(
                {
                    "state": str(error),
                    "promotion_decided": False,
                    "execution_ready": False,
                    "auto_trading_enabled": False,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 2


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
