"""Redacted operator for the optional calendar News Gate collector."""

from __future__ import annotations

import argparse
import json
import signal
import time
from collections.abc import Callable

from .news_gate import CalendarGateway, NewsGateCollector, NewsGateUnavailable
from .news_gate_config import NewsGateConfig, NewsGateConfigInvalid, load_news_gate_config


def emit(state: str, *, news_ready: bool = False) -> None:
    print(
        json.dumps(
            {
                "state": state,
                "news_ready": news_ready,
                "execution_ready": False,
                "auto_trading_enabled": False,
            }
        ),
        flush=True,
    )


def process(
    config: NewsGateConfig,
    collector: NewsGateCollector,
    *,
    once: bool,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    failures = 0
    while True:
        try:
            collector.refresh()
            failures = 0
            emit("READY", news_ready=True)
        except NewsGateUnavailable:
            failures += 1
            emit("UNAVAILABLE")
            if once:
                return 3
            if failures >= 5:
                emit("RETRY_BUDGET_EXHAUSTED")
                return 3
        if once:
            return 0
        sleep(config.poll_seconds if not failures else min(2 ** failures, config.poll_seconds))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise NewsGateConfigInvalid()


def main(argv=None) -> int:
    try:
        parser = Parser(description="Demo News Gate collector; private config from environment")
        parser.add_argument("action", choices=("status", "run"))
        parser.add_argument("--once", action="store_true")
        args = parser.parse_args(argv)
        if args.once and args.action != "run":
            raise NewsGateConfigInvalid()
        config = load_news_gate_config()
        if config is None:
            emit("DISABLED")
            return 0
        if args.action == "status":
            emit("CONFIGURED")
            return 0
        collector = NewsGateCollector(config, CalendarGateway(config))
        return process(config, collector, once=args.once)
    except NewsGateConfigInvalid as error:
        emit(str(error))
        return 2
    except KeyboardInterrupt:
        emit("STOPPED")
        return 130
    except Exception:
        emit("NEWS_GATE_WORKER_FAILED")
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
