from __future__ import annotations

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st
from sochron1k.models import ContractSpec, RiskContext
from sochron1k.risk import size_position


def test_ac02_rounds_down_and_stays_within_every_budget(contract, risk) -> None:
    decision = size_position(risk, contract)
    assert decision.allowed
    assert decision.volume == Decimal("0.25")
    assert decision.estimated_loss == Decimal("250.00")
    assert decision.estimated_loss <= decision.available_risk


def test_ac02_uses_remaining_daily_headroom(contract) -> None:
    context = RiskContext(
        equity=Decimal("99200"),
        daily_baseline=Decimal("99800"),
        experiment_baseline=Decimal("100000"),
        reserved_loss=Decimal("0"),
        loss_per_lot=Decimal("1000"),
        costs_per_lot=Decimal("100"),
        free_margin=Decimal("50000"),
        margin_per_lot=Decimal("1000"),
    )
    decision = size_position(context, contract)
    assert decision.allowed
    assert decision.available_risk == Decimal("148.5000")
    assert decision.volume == Decimal("0.13")
    assert decision.estimated_loss == Decimal("143.00")


def test_ac02_rejects_minimum_volume_when_it_exceeds_budget(contract) -> None:
    context = RiskContext(
        equity=Decimal("98005"),
        daily_baseline=Decimal("98005"),
        experiment_baseline=Decimal("100000"),
        loss_per_lot=Decimal("1000"),
        costs_per_lot=Decimal("0"),
        free_margin=Decimal("50000"),
        margin_per_lot=Decimal("1000"),
    )
    decision = size_position(context, contract)
    assert not decision.allowed
    assert decision.reason == "MINIMUM_VOLUME_EXCEEDS_RISK"
    assert decision.available_risk == Decimal("5.00")


@given(
    equity=st.integers(min_value=10_000, max_value=1_000_000),
    loss_per_lot=st.integers(min_value=100, max_value=100_000),
    reserved=st.integers(min_value=0, max_value=20),
)
def test_ac02_property_allowed_volume_never_exceeds_available_risk(
    equity, loss_per_lot, reserved
) -> None:
    contract = ContractSpec(
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
    money = Decimal(equity)
    context = RiskContext(
        equity=money,
        daily_baseline=money,
        experiment_baseline=money,
        reserved_loss=Decimal(reserved),
        loss_per_lot=Decimal(loss_per_lot),
        costs_per_lot=Decimal("1"),
        free_margin=money,
        margin_per_lot=Decimal("1000"),
    )
    decision = size_position(context, contract)
    if decision.allowed:
        assert decision.volume >= contract.volume_min
        assert decision.volume <= contract.volume_max
        assert decision.volume % contract.volume_step == 0
        assert decision.estimated_loss <= decision.available_risk
