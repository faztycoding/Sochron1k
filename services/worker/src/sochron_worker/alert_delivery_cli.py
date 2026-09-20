"""Explicit alert-delivery operator; importing this module performs no work."""

from __future__ import annotations

import argparse
import json
import signal
import time
from collections.abc import Callable

from .alert_delivery_config import (
    AlertDeliveryConfig,
    AlertDeliveryConfigInvalid,
    load_alert_delivery_config,
)
from .alert_delivery_driver import (
    AlertDeliveryDriver,
    AlertDestinationConflict,
    AlertDestinationUnavailable,
    AlertSendBudgetExhausted,
    AlertSourceUnavailable,
)
from .alert_delivery_http import HttpAlertDestination, HttpAlertSource
from .alert_delivery_journal import (
    AlertDeliveryJournal,
    AlertDeliveryJournalStatus,
    AlertDeliveryJournalUnavailable,
)


def _worker_state(status: AlertDeliveryJournalStatus, max_sends: int) -> str:
    if status.quarantined:
        return "QUARANTINED"
    if status.pending is None:
        return "IDLE"
    if status.pending.state == "UNKNOWN" and status.pending.attempts >= max_sends:
        return "RETRY_BUDGET_EXHAUSTED"
    return status.pending.state


def emit(state: str, journal: AlertDeliveryJournal | None = None) -> None:
    result: dict = {
        "state": state,
        "execution_ready": False,
        "auto_trading_enabled": False,
    }
    if journal is not None:
        status = journal.status()
        result.update(
            pending=status.pending.state if status.pending else None,
            attempts=status.pending.attempts if status.pending else 0,
            verified=status.verified,
            quarantined=status.quarantined,
            last_delivery_ref=status.last_verified_id,
            database_bytes=status.database_bytes,
        )
    print(json.dumps(result, separators=(",", ":")), flush=True)


def _publish(journal: AlertDeliveryJournal, state: str, config: AlertDeliveryConfig) -> None:
    journal.publish_status(
        state,
        heartbeat_seconds=max(60, min(config.poll_seconds * 3, 900)),
    )


def process(
    journal: AlertDeliveryJournal,
    driver: AlertDeliveryDriver,
    config: AlertDeliveryConfig,
    *,
    once: bool = False,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    unresolved = 0
    while True:
        try:
            state = driver.step()
        except AlertSendBudgetExhausted:
            state = "RETRY_BUDGET_EXHAUSTED"
        except AlertSourceUnavailable, AlertDestinationUnavailable:
            _publish(journal, "DEGRADED", config)
            emit("DEGRADED", journal)
            return 3
        _publish(journal, state, config)
        emit(state, journal)
        if state == "QUARANTINED":
            return 2
        if state == "RETRY_BUDGET_EXHAUSTED":
            return 3
        if state in {"UNKNOWN", "PREPARED"}:
            unresolved += 1
        else:
            unresolved = 0
        if once:
            return 0 if state in {"VERIFIED", "IDLE"} else 3
        delay = (
            min(2 ** max(unresolved - 1, 0), config.poll_seconds)
            if unresolved
            else config.poll_seconds
        )
        sleep(delay)


def operate(config: AlertDeliveryConfig, action: str, *, once: bool = False) -> int:
    source_token, destination_token = config.credentials()
    with AlertDeliveryJournal(
        config.state_directory,
        source_origin=config.source_origin,
        destination_origin=config.destination_origin,
        destination_ref=config.destination_ref,
        create=action == "init",
    ) as journal:
        source = HttpAlertSource(config.source_origin, source_token)
        destination = HttpAlertDestination(
            config.destination_origin, config.destination_ref, destination_token
        )
        driver = AlertDeliveryDriver(journal, source, destination, max_sends=config.max_sends)
        if action in {"init", "status"}:
            state = (
                "INITIALIZED"
                if action == "init"
                else _worker_state(journal.status(), config.max_sends)
            )
            _publish(
                journal,
                "IDLE" if state == "INITIALIZED" else state,
                config,
            )
            emit(state, journal)
            return 0
        if action == "reconcile":
            state = driver.reconcile_pending()
            projection = _worker_state(journal.status(), config.max_sends)
            _publish(journal, projection, config)
            emit(state, journal)
            return (
                0 if state in {"VERIFIED", "NO_PENDING"} else (2 if state == "QUARANTINED" else 3)
            )
        return process(journal, driver, config, once=once)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        del message
        raise AlertDeliveryConfigInvalid()


def main(argv=None) -> int:
    try:
        parser = Parser(description="Demo alert delivery; private config path from environment")
        parser.add_argument("action", choices=("init", "status", "run", "reconcile"))
        parser.add_argument("--once", action="store_true")
        args = parser.parse_args(argv)
        if args.once and args.action != "run":
            raise AlertDeliveryConfigInvalid()
        config = load_alert_delivery_config()
        if config is None:
            emit("DISABLED")
            return 0
        return operate(config, args.action, once=args.once)
    except (
        AlertDeliveryConfigInvalid,
        AlertDeliveryJournalUnavailable,
        AlertSourceUnavailable,
        AlertDestinationUnavailable,
        AlertDestinationConflict,
        AlertSendBudgetExhausted,
    ) as error:
        emit(str(error))
        return 2
    except KeyboardInterrupt:
        emit("STOPPED")
        return 130
    except Exception:
        emit("ALERT_DELIVERY_FAILED")
        return 2


def stop(signum, frame):
    del signum, frame
    raise KeyboardInterrupt()


def cli() -> int:
    previous = signal.signal(signal.SIGTERM, stop)
    try:
        return main()
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    raise SystemExit(cli())
