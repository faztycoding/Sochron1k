from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sochron1k.models import (
    AccountSnapshot,
    CommandIntent,
    ContractSpec,
    MarketSnapshot,
    RiskContext,
    Side,
    TradeMode,
)
from sochron1k.preflight import PreflightPolicy


@pytest.fixture
def observed_at() -> datetime:
    return datetime(2026, 9, 17, 2, 0, tzinfo=UTC)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def policy() -> PreflightPolicy:
    return PreflightPolicy(
        account_ref="demo-account-1",
        server="Demo-Server",
        symbol="XAUUSD",
        currency="THB",
        margin_mode="hedging",
    )


@pytest.fixture
def account(observed_at: datetime) -> AccountSnapshot:
    return AccountSnapshot(
        account_ref="demo-account-1",
        server="Demo-Server",
        currency="THB",
        margin_mode="hedging",
        trade_mode=TradeMode.DEMO,
        can_trade=True,
        equity=Decimal("100000"),
        checked_at=observed_at,
    )


@pytest.fixture
def contract() -> ContractSpec:
    return ContractSpec(
        symbol="XAUUSD",
        digits=2,
        tick_size=Decimal("0.01"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("100"),
        volume_step=Decimal("0.01"),
        stops_level_points=10,
        freeze_level_points=0,
        filling_modes=("ioc",),
    )


@pytest.fixture
def market(observed_at: datetime) -> MarketSnapshot:
    return MarketSnapshot(
        symbol="XAUUSD",
        bid=Decimal("2500.10"),
        ask=Decimal("2500.20"),
        event_time=observed_at - timedelta(milliseconds=50),
        received_time=observed_at - timedelta(milliseconds=20),
        market_open=True,
    )


@pytest.fixture
def intent(observed_at: datetime) -> CommandIntent:
    return CommandIntent(
        command_id="cmd-00000001",
        idempotency_key="idem-00000001",
        account_ref="demo-account-1",
        experiment_id="exp-pa01-v1",
        signal_id="sig-00000001",
        strategy_version="PA01-v1",
        symbol="XAUUSD",
        side=Side.BUY,
        requested_entry=Decimal("2500.20"),
        stop_loss=Decimal("2495.20"),
        take_profit=Decimal("2510.20"),
        expires_at=observed_at + timedelta(seconds=30),
    )


@pytest.fixture
def risk() -> RiskContext:
    return RiskContext(
        equity=Decimal("100000"),
        daily_baseline=Decimal("100000"),
        experiment_baseline=Decimal("100000"),
        reserved_loss=Decimal("0"),
        loss_per_lot=Decimal("1000"),
        costs_per_lot=Decimal("0"),
        free_margin=Decimal("50000"),
        margin_per_lot=Decimal("1000"),
    )
