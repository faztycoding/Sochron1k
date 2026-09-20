"""Explicit operator for one default-off research-evaluation publication."""

from __future__ import annotations

import argparse
import json

from .research_evaluation import ResearchEvaluationInvalid, evaluate_bundle, load_bundle
from .research_evaluation_config import (
    ResearchEvaluationConfig,
    ResearchEvaluationConfigInvalid,
    load_research_evaluation_config,
)
from .research_evaluation_driver import (
    ResearchEvaluationDriver,
    ResearchEvaluationSendBudgetExhausted,
)
from .research_evaluation_http import ResearchEvaluationSupabaseDestination
from .research_evaluation_journal import (
    ResearchEvaluationJournal,
    ResearchEvaluationJournalUnavailable,
)


def emit(state: str, journal: ResearchEvaluationJournal | None = None) -> None:
    result: dict = {
        "state": state,
        "statistics_source_ready": state == "VERIFIED",
        "promotion_decided": False,
        "execution_ready": False,
        "auto_trading_enabled": False,
    }
    if journal is not None:
        status = journal.status()
        result.update(
            evaluation_fingerprint=status.pending.fingerprint,
            attempts=status.pending.attempts,
            storage=status.storage,
        )
    print(json.dumps(result), flush=True)


def operate(config: ResearchEvaluationConfig, action: str) -> int:
    bundle = load_bundle(config.input_file)
    envelope = evaluate_bundle(bundle)
    with ResearchEvaluationJournal(
        config.state_directory,
        envelope,
        config.input_file,
        config.owner_id,
        config.strategy_version_id,
        config.experiment_id,
        config.origin,
        create=action == "init",
    ) as journal:
        if action in {"init", "status"}:
            emit("INITIALIZED" if action == "init" else journal.status().pending.state, journal)
            return 0
        destination = ResearchEvaluationSupabaseDestination(config)
        driver = ResearchEvaluationDriver(journal, destination)
        state = driver.reconcile_pending() if action == "reconcile" else driver.step()
        emit(state, journal)
        return 0 if state in {"VERIFIED", "REVIEW_REQUIRED"} else 3


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ResearchEvaluationConfigInvalid()


def main(argv=None) -> int:
    try:
        parser = Parser(description="Demo research evaluation producer; private config required")
        parser.add_argument("action", choices=("init", "status", "publish", "reconcile"))
        args = parser.parse_args(argv)
        config = load_research_evaluation_config()
        if config is None:
            emit("DISABLED")
            return 0
        return operate(config, args.action)
    except (
        ResearchEvaluationConfigInvalid,
        ResearchEvaluationInvalid,
        ResearchEvaluationJournalUnavailable,
        ResearchEvaluationSendBudgetExhausted,
    ) as error:
        emit(str(error))
        return 2


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
