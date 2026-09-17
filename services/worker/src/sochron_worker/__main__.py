"""Explicit local operator entry point; importing this module performs no work."""

from __future__ import annotations

import argparse
import json
import signal
import time
from collections.abc import Callable

from .native_source import NativeArchiveSource, SourceUnavailable
from .sync_config import SyncConfig, SyncConfigInvalid, load_config
from .sync_driver import SendBudgetExhausted, SyncDriver
from .sync_http import SupabaseDestination
from .sync_journal import JournalUnavailable, SyncJournal


def emit(state: str, journal: SyncJournal | None = None) -> None:
    result: dict = {"state": state, "execution_ready": False, "auto_trading_enabled": False}
    if journal is not None:
        status = journal.status()
        result.update(
            cursor_receipt=status.cursor.receipt,
            cursor_time_server_s=status.cursor.time_server_s,
            pending=status.pending.state if status.pending else None,
            attempts=status.pending.attempts if status.pending else 0,
            database_bytes=status.database_bytes,
            storage=status.storage,
        )
    print(json.dumps(result), flush=True)


def process(
    journal: SyncJournal,
    driver: SyncDriver,
    *,
    once=False,
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


def operate(config: SyncConfig, action: str, *, once=False) -> int:
    source = NativeArchiveSource(
        config.source_directory,
        config.archive_id,
        config.identity,
        config.offset_seconds,
        config.chart,
    )
    with SyncJournal(
        config.state_directory, source, config.owner_id, config.origin, create=action == "init"
    ) as journal:
        if action in {"init", "status"}:
            emit("INITIALIZED" if action == "init" else "LOCAL_STATUS", journal)
            return 0
        destination = SupabaseDestination(config)
        return process(journal, SyncDriver(journal, destination), once=once)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default includes arbitrary rejected arguments, possibly credentials.
        raise SyncConfigInvalid()


def main(argv=None) -> int:
    try:
        parser = Parser(description="Demo native M1 sync; private config path from environment")
        parser.add_argument("action", choices=("init", "status", "run"))
        parser.add_argument("--once", action="store_true")
        args = parser.parse_args(argv)
        if args.once and args.action != "run":
            raise SyncConfigInvalid()
        config = load_config()
        if config is None:
            emit("DISABLED")
            return 0
        return operate(config, args.action, once=args.once)
    except (SyncConfigInvalid, SourceUnavailable, JournalUnavailable, SendBudgetExhausted) as error:
        emit(str(error))
        return 2
    except KeyboardInterrupt:
        emit("STOPPED")
        return 130
    except Exception:
        # Do not leak request headers, account fields, paths or exception context.
        emit("SYNC_WORKER_FAILED")
        return 2


def stop(signum, frame):
    raise KeyboardInterrupt()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    raise SystemExit(main())
