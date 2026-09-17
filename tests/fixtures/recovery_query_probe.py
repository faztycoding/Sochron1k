"""Synthetic installed-artifact probe; never an owner activation tool."""

import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from sochron1k.journal import Journal
from sochron1k.models import BrokerSnapshot, CommandState
from sochron1k.service import ExecutionService


class QueryOnlySimulator:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.mode = "unavailable"
        self.queries = 0

    def send(self, *args, **kwargs):
        raise AssertionError("restored recovery tried to dispatch")

    def query(self, command_id):
        assert command_id == self.snapshot.command_id
        self.queries += 1
        if self.mode == "unavailable":
            raise ConnectionError("synthetic query failure")
        return None if self.mode == "missing" else self.snapshot


def probe(path, broker_file):
    snapshot = BrokerSnapshot.model_validate_json(broker_file.read_text())
    journal = Journal(path)
    adapter = QueryOnlySimulator(snapshot)
    service = ExecutionService(journal, adapter)
    before = journal.counts()
    with closing(sqlite3.connect(path)) as db:
        risk_before = db.execute("SELECT * FROM risk_state").fetchall()
    assert service.recover() == {snapshot.command_id: CommandState.UNKNOWN}
    adapter.mode = "missing"
    assert service.recover() == {snapshot.command_id: CommandState.UNKNOWN}
    assert journal.counts() == before
    adapter.mode = "exact"
    for _ in range(2):
        assert service.recover() == {snapshot.command_id: CommandState.FILLED}
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT * FROM risk_state").fetchall() == risk_before
        assert db.execute("SELECT daily_halt,total_halt FROM risk_state").fetchone() == (1, 1)
        assert db.execute("SELECT state,protected FROM commands").fetchone() == ("filled", 1)
        assert db.execute("SELECT count(*) FROM dispatch_attempts").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM exposure_slots").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM broker_deals").fetchone()[0] == 1
        assert db.execute("SELECT order_ticket,position_id FROM broker_orders").fetchone() == (
            snapshot.order_ticket,
            snapshot.position_id,
        )
    print(
        json.dumps(
            dict(
                result="PASS",
                broker="query-only-simulator",
                queries=adapter.queries,
                sends=0,
                execution_ready=False,
                auto_trading_enabled=False,
            )
        )
    )


if __name__ == "__main__":
    probe(Path(sys.argv[1]), Path(sys.argv[2]))
