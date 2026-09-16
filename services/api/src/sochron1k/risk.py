from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal

from .models import ContractSpec, RiskContext, RiskDecision

RISK_PER_TRADE = Decimal("0.0025")
DAILY_LOSS_LIMIT = Decimal("0.0075")
EXPERIMENT_LOSS_LIMIT = Decimal("0.02")


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def size_position(context: RiskContext, contract: ContractSpec) -> RiskDecision:
    current_daily_loss = max(Decimal("0"), context.daily_baseline - context.equity)
    current_experiment_loss = max(Decimal("0"), context.experiment_baseline - context.equity)
    per_trade = context.equity * RISK_PER_TRADE
    daily_remaining = context.daily_baseline * DAILY_LOSS_LIMIT - current_daily_loss
    experiment_remaining = (
        context.experiment_baseline * EXPERIMENT_LOSS_LIMIT - current_experiment_loss
    )
    available = min(per_trade, daily_remaining, experiment_remaining) - context.reserved_loss
    if available <= 0:
        return RiskDecision(allowed=False, reason="RISK_BUDGET_EXHAUSTED")

    loss_and_cost_per_lot = context.loss_per_lot + context.costs_per_lot
    raw_volume = available / loss_and_cost_per_lot
    margin_limited_volume = context.free_margin / context.margin_per_lot
    volume = _floor_to_step(
        min(raw_volume, margin_limited_volume, contract.volume_max), contract.volume_step
    )

    minimum_loss = contract.volume_min * loss_and_cost_per_lot
    minimum_margin = contract.volume_min * context.margin_per_lot
    if minimum_loss > available:
        return RiskDecision(
            allowed=False,
            reason="MINIMUM_VOLUME_EXCEEDS_RISK",
            available_risk=available,
            estimated_loss=minimum_loss,
            estimated_margin=minimum_margin,
        )
    if minimum_margin > context.free_margin:
        return RiskDecision(
            allowed=False,
            reason="INSUFFICIENT_MARGIN",
            available_risk=available,
            estimated_loss=minimum_loss,
            estimated_margin=minimum_margin,
        )
    if volume < contract.volume_min:
        return RiskDecision(allowed=False, reason="VOLUME_BELOW_MINIMUM", available_risk=available)

    estimated_loss = volume * loss_and_cost_per_lot
    estimated_margin = volume * context.margin_per_lot
    if estimated_loss > available:
        return RiskDecision(allowed=False, reason="ROUNDED_VOLUME_EXCEEDS_RISK")
    return RiskDecision(
        allowed=True,
        volume=volume,
        available_risk=available,
        estimated_loss=estimated_loss,
        estimated_margin=estimated_margin,
    )
