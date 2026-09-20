"""Explicit PA01 producer operator; importing this module performs no work."""

from __future__ import annotations

import argparse
import json
import signal
import time
from collections.abc import Callable

from .native_source import NativeArchiveSource, SourceUnavailable
from .pa01_config import PA01ConfigInvalid, PA01ProducerConfig, load_pa01_config
from .pa01_driver import PA01ProducerDriver, PA01SendBudgetExhausted
from .pa01_http import PA01SupabaseDestination
from .pa01_journal import PA01JournalUnavailable, PA01ProducerJournal
from .pa01_source import PA01DecisionSource, PA01SourceUnavailable, PolicyFileSource


def emit(state: str, journal: PA01ProducerJournal | None = None) -> None:
    result: dict = {"state": state, "execution_ready": False, "auto_trading_enabled": False}
    if journal is not None:
        status = journal.status()
        result.update(
            last_formed_at=(
                status.last_formed_at.isoformat(timespec="microseconds")
                if status.last_formed_at
                else None
            ),
            last_fingerprint=status.last_fingerprint,
            pending=status.pending.state if status.pending else None,
            attempts=status.pending.attempts if status.pending else 0,
            database_bytes=status.database_bytes,
            storage=status.storage,
        )
    print(json.dumps(result), flush=True)


def process(
    journal: PA01ProducerJournal,
    driver: PA01ProducerDriver,
    *,
    once: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    unresolved = 0
    while True:
        state = driver.step()
        emit(state, journal)
        if state == "QUARANTINED":
            return 2
        if state in {"UNKNOWN", "PREPARED"}:
            unresolved += 1
            if unresolved >= 5:
                emit("RETRY_BUDGET_EXHAUSTED", journal)
                return 3
        else:
            unresolved = 0
        if once:
            return 0 if state in {"VERIFIED", "IDLE"} else 3
        sleep(min(2 ** (unresolved - 1), 30) if unresolved else 2)


def operate(config: PA01ProducerConfig, action: str, *, once: bool = False) -> int:
    archive = NativeArchiveSource(
        config.source_directory,
        config.archive_id,
        config.identity,
        config.offset_seconds,
        config.chart,
    )
    source = PA01DecisionSource(archive, PolicyFileSource(config.policy_file), config.code_hash)
    with PA01ProducerJournal(
        config.state_directory,
        source,
        config.owner_id,
        config.strategy_version_id,
        config.experiment_id,
        config.origin,
        create=action == "init",
    ) as journal:
        if action in {"init", "status"}:
            emit("INITIALIZED" if action == "init" else "LOCAL_STATUS", journal)
            return 0
        destination = PA01SupabaseDestination(config)
        driver = PA01ProducerDriver(journal, destination)
        if action == "reconcile":
            state = driver.reconcile_pending()
            emit(state, journal)
            if state in {"VERIFIED", "NO_PENDING"}:
                return 0
            return 2 if state == "QUARANTINED" else 3
        return process(journal, driver, once=once)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise PA01ConfigInvalid()


def main(argv=None) -> int:
    try:
        parser = Parser(description="Demo PA01 producer; private config path from environment")
        parser.add_argument("action", choices=("init", "status", "run", "reconcile"))
        parser.add_argument("--once", action="store_true")
        args = parser.parse_args(argv)
        if args.once and args.action != "run":
            raise PA01ConfigInvalid()
        config = load_pa01_config()
        if config is None:
            emit("DISABLED")
            return 0
        return operate(config, args.action, once=args.once)
    except (
        PA01ConfigInvalid,
        PA01SourceUnavailable,
        SourceUnavailable,
        PA01JournalUnavailable,
        PA01SendBudgetExhausted,
    ) as error:
        emit(str(error))
        return 2
    except KeyboardInterrupt:
        emit("STOPPED")
        return 130
    except Exception:
        emit("PA01_WORKER_FAILED")
        return 2


def stop(signum, frame):
    raise KeyboardInterrupt()


def cli() -> int:
    previous = signal.signal(signal.SIGTERM, stop)
    try:
        return main()
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    raise SystemExit(cli())
