"""Create one synthetic confirmed journal record for the browser verifier."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sochron1k.journal import Journal
from sochron1k.models import BrokerDeal, BrokerSnapshot, CommandIntent, Side


def seed(path: Path) -> None:
    assert path.is_absolute() and not path.exists()
    now = datetime.now(UTC)
    intent = CommandIntent(
        command_id="browser-command-confirmed",
        idempotency_key="browser-command-confirmed",
        account_ref="synthetic-browser-account",
        experiment_id="browser-experiment",
        signal_id="browser-signal",
        strategy_version="browser-fixture-v1",
        symbol="XAUUSD.fixture",
        side=Side.BUY,
        requested_entry=Decimal("2500.10"),
        stop_loss=Decimal("2490.10"),
        take_profit=Decimal("2520.10"),
        expires_at=now + timedelta(minutes=5),
    )
    journal = Journal(path)
    journal.reserve(intent, Decimal("0.10"), Decimal("100"))
    journal.begin_dispatch(
        intent.command_id, "browser-attempt", Decimal("1000"), Decimal("0")
    )
    journal.apply_broker_snapshot(
        BrokerSnapshot(
            command_id=intent.command_id,
            order_ticket="browser-order-confirmed",
            position_id="browser-position-confirmed",
            requested_volume=Decimal("0.10"),
            filled_volume=Decimal("0.10"),
            remaining_volume=Decimal("0"),
            deals=(
                BrokerDeal(
                    deal_ticket="browser-deal-confirmed",
                    volume=Decimal("0.10"),
                    price=Decimal("2500.10"),
                    occurred_at=now,
                ),
            ),
            stop_loss_confirmed=True,
        )
    )
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(path) + suffix)
        if candidate.exists():
            candidate.chmod(0o600)
    print(json.dumps({"result": "PASS", "commands": 1, "execution_ready": False}))


if __name__ == "__main__":
    seed(Path(sys.argv[1]))
