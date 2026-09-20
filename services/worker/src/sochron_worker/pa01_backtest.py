"""Offline point-in-time PA01 replay; no network, promotion or execution authority."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from bisect import bisect_left, bisect_right
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation, localcontext
from itertools import pairwise
from pathlib import Path
from typing import Literal, Self

from pydantic import (
    AwareDatetime,
    Field,
    StrictBool,
    StrictInt,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from .native_source import _object
from .pa01 import (
    ENTRY_DRIFT_MAX_ATR,
    EXPIRY_SECONDS,
    M5_SECONDS,
    PARAMETER_HASH,
    PARAMETER_VERSION,
    STRATEGY_VERSION,
    TARGET_R,
    TIME_EXIT_BARS,
    ClosedBar,
    PA01Context,
    PA01Decision,
    evaluate_pa01,
)
from .research_evaluation import (
    BUNDLE_PROTOCOL,
    HASH_PATTERN,
    MAX_BUNDLE_BYTES,
    MAX_MONEY,
    BootstrapPlan,
    ClosedTrade,
    CostAssumptions,
    EquitySample,
    EvaluationSplit,
    EvaluationWindow,
    ExactModel,
    ExcludedRecord,
    ResearchBundle,
    ResearchEvaluationInvalid,
    _finite,
    _positive,
    bundle_dict,
)
from .sync_config import SyncConfigInvalid, canonical_path, private_bytes
from .sync_journal import canonical

INPUT_PROTOCOL = "sochron.pa01-tick-replay.v1"
PRODUCER_REVISION = "SCN-030/pa01-tick-replay-v1.0.0"
PA01_CODE_HASH = hashlib.sha256(Path(__file__).with_name("pa01.py").read_bytes()).hexdigest()
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_M5_BARS = 20_000
MAX_H1_BARS = 2_000
MAX_TICKS = 500_000
MAX_POLICIES = 20_000
MAX_TICK_GAP_SECONDS = 5
TIME_EXIT_SECONDS = TIME_EXIT_BARS * M5_SECONDS
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class PA01BacktestInvalid(RuntimeError):
    def __init__(self) -> None:
        super().__init__("PA01_BACKTEST_INVALID")


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _safe(value: str) -> str:
    if not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("safe text required")
    return value


def _grid(value: Decimal, tick_size: Decimal, digits: int) -> bool:
    value_num, value_den = value.as_integer_ratio()
    tick_num, tick_den = tick_size.as_integer_ratio()
    return not (
        value_num * tick_den % (value_den * tick_num)
        or value_num * 10**digits % value_den
    )


class ReplayTick(ExactModel):
    tick_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
    event_time_utc: AwareDatetime
    available_at_utc: AwareDatetime
    bid: Decimal = Field(gt=0)
    ask: Decimal = Field(gt=0)

    @field_validator("event_time_utc", "available_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)

    @field_validator("bid", "ask")
    @classmethod
    def exact_price(cls, value: Decimal) -> Decimal:
        return _positive(value)

    @model_validator(mode="after")
    def causal_quote(self) -> Self:
        if self.available_at_utc < self.event_time_utc or self.ask < self.bid:
            raise ValueError("invalid tick causality")
        return self


class ReplayPolicy(ExactModel):
    m5_evidence_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
    observed_at_utc: AwareDatetime
    source_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
    market_open: StrictBool
    news_blocked: StrictBool

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)


class PA01BacktestInput(ExactModel):
    protocol: Literal["sochron.pa01-tick-replay.v1"] = INPUT_PROTOCOL
    producer_revision: Literal["SCN-030/pa01-tick-replay-v1.0.0"] = PRODUCER_REVISION
    source_dataset_hash: str = Field(pattern=HASH_PATTERN)
    strategy_version: Literal["PA01-v1"] = STRATEGY_VERSION
    parameter_version: Literal["PA01-v1.0.1"] = PARAMETER_VERSION
    parameter_hash: str = Field(pattern=HASH_PATTERN)
    strategy_code_hash: str = Field(pattern=HASH_PATTERN)
    feed_id: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[^\s]+$")
    broker_utc_offset_seconds: StrictInt = Field(ge=-50_400, le=50_400)
    tick_size: Decimal = Field(gt=0)
    digits: StrictInt = Field(ge=0, le=10)
    split: EvaluationSplit
    evaluation_window: EvaluationWindow
    cost_assumptions: CostAssumptions
    bootstrap: BootstrapPlan
    initial_equity: Decimal
    filled_volume_lots: Decimal
    point_value_per_lot: Decimal
    swap_cost_per_trade: Decimal = Field(ge=0)
    m5_bars: tuple[ClosedBar, ...] = Field(min_length=1, max_length=MAX_M5_BARS)
    h1_bars: tuple[ClosedBar, ...] = Field(min_length=1, max_length=MAX_H1_BARS)
    policies: tuple[ReplayPolicy, ...] = Field(min_length=1, max_length=MAX_POLICIES)
    ticks: tuple[ReplayTick, ...] = Field(min_length=2, max_length=MAX_TICKS)

    @field_validator("feed_id")
    @classmethod
    def safe_feed(cls, value: str) -> str:
        return _safe(value)

    @field_validator(
        "tick_size",
        "initial_equity",
        "filled_volume_lots",
        "point_value_per_lot",
        "swap_cost_per_trade",
    )
    @classmethod
    def exact_bounded_decimal(cls, value: Decimal) -> Decimal:
        return _positive(value) if value != 0 else value

    @model_validator(mode="after")
    def complete_point_in_time_evidence(self) -> Self:
        source_payload = self.model_dump(mode="json", exclude={"source_dataset_hash"})
        if (
            hashlib.sha256(canonical(source_payload).encode()).hexdigest()
            != self.source_dataset_hash
        ):
            raise ValueError("source dataset hash mismatch")
        if (
            self.parameter_hash != PARAMETER_HASH
            or self.strategy_code_hash != PA01_CODE_HASH
            or self.broker_utc_offset_seconds % 60
        ):
            raise ValueError("unrecognized PA01 or broker-time identity")
        if not _grid(self.tick_size, self.tick_size, self.digits):
            raise ValueError("invalid tick grid")
        if self.initial_equity > MAX_MONEY:
            raise ValueError("initial equity is unbounded")
        if not self.cost_assumptions.swap_included and self.swap_cost_per_trade != 0:
            raise ValueError("swap evidence present while excluded")

        bars = self.m5_bars + self.h1_bars
        evidence_ids = [bar.evidence_id for bar in bars]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("duplicate bar evidence")
        for timeframe, selected in (("M5", self.m5_bars), ("H1", self.h1_bars)):
            if [bar.time_server_s for bar in selected] != sorted(
                {bar.time_server_s for bar in selected}
            ):
                raise ValueError("bars must be strictly ordered")
            if any(
                bar.timeframe != timeframe
                or bar.feed_id != self.feed_id
                or bar.symbol != self.symbol
                or bar.broker_utc_offset_seconds != self.broker_utc_offset_seconds
                or bar.tick_size != self.tick_size
                or bar.digits != self.digits
                for bar in selected
            ):
                raise ValueError("mixed bar binding")

        ticks = self.ticks
        if len({tick.tick_id for tick in ticks}) != len(ticks):
            raise ValueError("duplicate tick ID")
        if any(
            later.event_time_utc <= earlier.event_time_utc
            or later.available_at_utc <= earlier.available_at_utc
            for earlier, later in pairwise(ticks)
        ):
            raise ValueError("ticks must be strictly ordered")
        if any(
            not _grid(tick.bid, self.tick_size, self.digits)
            or not _grid(tick.ask, self.tick_size, self.digits)
            for tick in ticks
        ):
            raise ValueError("tick is outside the admitted grid")
        window = self.evaluation_window
        replay_start = window.start_utc - timedelta(seconds=M5_SECONDS)
        if ticks[0].event_time_utc > replay_start or ticks[-1].event_time_utc < window.end_utc:
            raise ValueError("tick stream does not cover the evaluation window")
        event_times = [tick.event_time_utc for tick in ticks]
        left = max(0, bisect_right(event_times, replay_start) - 1)
        right = bisect_left(event_times, window.end_utc)
        if right >= len(ticks):
            raise ValueError("tick stream does not bracket the evaluation window")
        active = ticks[left : right + 1]
        if (
            len(active) < 2
            or active[0].event_time_utc > replay_start
            or active[-1].event_time_utc < window.end_utc
            or any(
            (later.event_time_utc - earlier.event_time_utc).total_seconds()
            > MAX_TICK_GAP_SECONDS
            for earlier, later in pairwise(active)
            )
        ):
            raise ValueError("active tick stream has a stale gap")
        maximum_spread = max((tick.ask - tick.bid) / self.tick_size for tick in active)
        if self.cost_assumptions.spread_points < maximum_spread:
            raise ValueError("fixed spread understates observed evidence")

        eligible = _eligible_m5(self)
        policy_ids = [policy.m5_evidence_id for policy in self.policies]
        if len(set(policy_ids)) != len(policy_ids) or set(policy_ids) != {
            bar.evidence_id for bar in eligible
        }:
            raise ValueError("policy schedule is incomplete or extra")
        by_id = {bar.evidence_id: bar for bar in eligible}
        for policy in self.policies:
            bar = by_id[policy.m5_evidence_id]
            policy_age = (bar.available_at_utc - policy.observed_at_utc).total_seconds()
            if not 0 <= policy_age <= MAX_TICK_GAP_SECONDS:
                raise ValueError("policy evidence was unavailable at decision")
            available_h1 = tuple(
                item
                for item in self.h1_bars
                if item.close_time_utc <= bar.available_at_utc
                and item.available_at_utc <= bar.available_at_utc
            )
            if (
                not available_h1
                or (
                    bar.available_at_utc - available_h1[-1].close_time_utc
                ).total_seconds()
                > 3_600 + MAX_TICK_GAP_SECONDS
            ):
                raise ValueError("H1 decision evidence is stale or incomplete")

        for bar in self.m5_bars:
            if not (window.start_utc <= bar.close_time_utc <= window.end_utc):
                continue
            left = bisect_left(event_times, bar.open_time_utc)
            right = bisect_left(event_times, bar.close_time_utc)
            children = ticks[left:right]
            if (
                not children
                or children[0].bid != bar.open
                or max(tick.bid for tick in children) != bar.high
                or min(tick.bid for tick in children) != bar.low
                or children[-1].bid != bar.close
            ):
                raise ValueError("tick path does not reproduce M5 OHLC")
            if right >= len(ticks) or ticks[right].available_at_utc != bar.available_at_utc:
                raise ValueError("M5 availability is not the next observed tick")
        return self


_INPUT = TypeAdapter(PA01BacktestInput)


def _eligible_m5(source: PA01BacktestInput) -> tuple[ClosedBar, ...]:
    window = source.evaluation_window
    offset = source.broker_utc_offset_seconds
    start_server = int(window.start_utc.timestamp()) + offset
    end_server = int(window.end_utc.timestamp()) + offset
    if (
        window.start_utc.microsecond
        or window.end_utc.microsecond
        or start_server % M5_SECONDS
        or end_server % M5_SECONDS
    ):
        raise ValueError("evaluation window must align to broker M5 boundaries")
    latest_close = end_server - EXPIRY_SECONDS - TIME_EXIT_SECONDS - MAX_TICK_GAP_SECONDS
    expected_opens = tuple(
        range(start_server - M5_SECONDS, latest_close - M5_SECONDS + 1, M5_SECONDS)
    )
    by_open = {bar.time_server_s: bar for bar in source.m5_bars}
    if any(opened not in by_open for opened in expected_opens):
        raise ValueError("M5 schedule has a missing decision boundary")
    return tuple(by_open[opened] for opened in expected_opens)


def _reject_float(_: str):
    raise ValueError("decimal JSON values must be exact strings")


def _reject_constant(_: str):
    raise ValueError("non-finite JSON number")


def _exact_utc(value: object) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("exact UTC timestamp required")
    parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    normalized = parsed.astimezone(UTC)
    admitted = {
        normalized.isoformat(timespec="seconds").replace("+00:00", "Z"),
        normalized.isoformat(timespec="microseconds").replace("+00:00", "Z"),
    }
    if value not in admitted:
        raise ValueError("normalized UTC timestamp required")


def backtest_dict(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw.encode()) > MAX_INPUT_BYTES:
        raise ValueError("invalid backtest input size")
    value = json.loads(
        raw,
        object_pairs_hook=_object,
        parse_float=_reject_float,
        parse_constant=_reject_constant,
    )
    if not isinstance(value, dict) or canonical(value) != raw:
        raise ValueError("canonical JSON object required")
    decimal_paths = (
        "tick_size",
        "initial_equity",
        "filled_volume_lots",
        "point_value_per_lot",
        "swap_cost_per_trade",
    )
    costs = value.get("cost_assumptions")
    if (
        any(not isinstance(value.get(key), str) for key in decimal_paths)
        or not isinstance(costs, dict)
        or any(
            not isinstance(costs.get(key), str)
            for key in (
                "spread_points",
                "slippage_points",
                "commission_per_lot",
                "operating_cost_per_trade",
            )
        )
    ):
        raise ValueError("decimal evidence must use strings")
    window = value.get("evaluation_window")
    policies = value.get("policies")
    if not isinstance(window, dict) or not isinstance(policies, list):
        raise ValueError("timestamp evidence required")
    for key in ("start_utc", "end_utc"):
        _exact_utc(window.get(key))
    prior = window.get("prior_development_cutoff_utc")
    if prior is not None:
        _exact_utc(prior)
    for collection, fields in (
        (value["m5_bars"], ("open_time_utc", "available_at_utc")),
        (value["h1_bars"], ("open_time_utc", "available_at_utc")),
        (value["ticks"], ("event_time_utc", "available_at_utc")),
        (policies, ("observed_at_utc",)),
    ):
        for item in collection:
            if not isinstance(item, dict):
                raise ValueError("timestamp evidence required")
            for field in fields:
                _exact_utc(item.get(field))
    for collection, fields in (
        (value.get("m5_bars"), ("open", "high", "low", "close", "tick_size")),
        (value.get("h1_bars"), ("open", "high", "low", "close", "tick_size")),
        (value.get("ticks"), ("bid", "ask")),
    ):
        if not isinstance(collection, list) or any(
            not isinstance(item, dict)
            or any(not isinstance(item.get(field), str) for field in fields)
            for item in collection
        ):
            raise ValueError("nested decimal evidence must use strings")
    supplied = value.get("source_dataset_hash")
    if not isinstance(supplied, str):
        raise ValueError("source dataset hash required")
    hashed = dict(value)
    del hashed["source_dataset_hash"]
    if hashlib.sha256(canonical(hashed).encode()).hexdigest() != supplied:
        raise ValueError("source dataset hash mismatch")
    for key in decimal_paths:
        value[key] = Decimal(value[key])
    for key in (
        "spread_points",
        "slippage_points",
        "commission_per_lot",
        "operating_cost_per_trade",
    ):
        costs[key] = Decimal(costs[key])
    for collection, fields in (
        (value["m5_bars"], ("open", "high", "low", "close", "tick_size")),
        (value["h1_bars"], ("open", "high", "low", "close", "tick_size")),
        (value["ticks"], ("bid", "ask")),
    ):
        for item in collection:
            for field in fields:
                item[field] = Decimal(item[field])
    return value


def load_backtest_input(path: Path) -> PA01BacktestInput:
    try:
        raw = private_bytes(path, MAX_INPUT_BYTES).decode("utf-8")
        return _INPUT.validate_python(backtest_dict(raw))
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        InvalidOperation,
        SyncConfigInvalid,
        ValidationError,
    ):
        raise PA01BacktestInvalid() from None


def _money_from_points(source: PA01BacktestInput, points: Decimal) -> Decimal:
    return points * source.point_value_per_lot * source.filled_volume_lots


def _net(source: PA01BacktestInput, gross: Decimal) -> Decimal:
    costs = source.cost_assumptions
    return _finite(
        gross
        - _money_from_points(source, costs.spread_points)
        - _money_from_points(source, costs.slippage_points)
        - costs.commission_per_lot * source.filled_volume_lots
        - source.swap_cost_per_trade
        - costs.operating_cost_per_trade
    )


def _record_evidence(
    source: PA01BacktestInput, policy: ReplayPolicy, decision: PA01Decision
) -> tuple[str, ...]:
    suffix = decision.decision_id[-16:]
    policy_hash = hashlib.sha256(policy.source_id.encode()).hexdigest()[:32]
    return (
        decision.decision_id,
        f"source:{source.source_dataset_hash}:{suffix}",
        f"policy:{policy_hash}:{suffix}",
    )


def _excluded(
    source: PA01BacktestInput,
    policy: ReplayPolicy,
    decision: PA01Decision,
    *,
    at: datetime,
    record_type: Literal["wait", "rejected", "ambiguous"],
    reason: str,
    horizon: datetime | None = None,
    available: datetime | None = None,
) -> ExcludedRecord:
    end = horizon or at
    return ExcludedRecord(
        type=record_type,
        setup_id=decision.setup_id,
        evidence_ids=_record_evidence(source, policy, decision),
        formed_at_utc=decision.formed_at_utc,
        decision_available_at_utc=decision.confirmed_at_utc,
        decision_at_utc=at,
        label_horizon_end_utc=end,
        outcome_available_at_utc=available or end,
        reason_code=reason,
    )


def _label_trade(
    source: PA01BacktestInput,
    policy: ReplayPolicy,
    decision: PA01Decision,
    decision_at: datetime,
    ticks: tuple[ReplayTick, ...],
    event_times: list[datetime],
) -> ClosedTrade | ExcludedRecord:
    first = bisect_right(event_times, decision.confirmed_at_utc)
    if first >= len(ticks):
        return _excluded(
            source,
            policy,
            decision,
            at=decision_at,
            record_type="rejected",
            reason="ENTRY_TICK_MISSING",
            horizon=decision.expires_at_utc,
            available=decision.expires_at_utc,
        )
    entry_tick = ticks[first]
    if entry_tick.available_at_utc > decision.expires_at_utc:
        return _excluded(
            source,
            policy,
            decision,
            at=decision_at,
            record_type="rejected",
            reason="ENTRY_EXPIRED",
            horizon=decision.expires_at_utc,
            available=entry_tick.available_at_utc,
        )
    atr = decision.features.atr14
    stop = decision.features.proposed_stop
    if atr is None or stop is None or atr <= 0:
        return _excluded(
            source,
            policy,
            decision,
            at=decision_at,
            record_type="rejected",
            reason="ENTRY_EVIDENCE_INVALID",
        )
    fill = entry_tick.ask if decision.action == "buy" else entry_tick.bid
    latest_close = next(
        bar.close for bar in reversed(source.m5_bars) if bar.evidence_id in decision.evidence_ids
    )
    if abs(fill - latest_close) > ENTRY_DRIFT_MAX_ATR * atr:
        return _excluded(
            source,
            policy,
            decision,
            at=decision_at,
            record_type="rejected",
            reason="ENTRY_DRIFT",
            horizon=entry_tick.event_time_utc,
            available=entry_tick.available_at_utc,
        )
    risk_price = fill - stop if decision.action == "buy" else stop - fill
    if risk_price <= 0:
        return _excluded(
            source,
            policy,
            decision,
            at=decision_at,
            record_type="rejected",
            reason="STOP_SIDE_INVALID",
            horizon=entry_tick.event_time_utc,
            available=entry_tick.available_at_utc,
        )
    scheduled_exit = entry_tick.event_time_utc + timedelta(seconds=TIME_EXIT_SECONDS)
    coverage_index = bisect_right(event_times, scheduled_exit) - 1
    if coverage_index < first:
        raise PA01BacktestInvalid()
    coverage = ticks[coverage_index]
    if scheduled_exit - coverage.event_time_utc > timedelta(seconds=MAX_TICK_GAP_SECONDS):
        raise PA01BacktestInvalid()
    target = (
        fill + TARGET_R * risk_price
        if decision.action == "buy"
        else fill - TARGET_R * risk_price
    )
    exit_tick = coverage
    label: Literal["TP_FIRST", "SL_FIRST", "TIME_EXIT"] = "TIME_EXIT"
    for tick in ticks[first + 1 : coverage_index + 1]:
        liquidation = tick.bid if decision.action == "buy" else tick.ask
        if decision.action == "buy":
            if liquidation <= stop:
                exit_tick, label = tick, "SL_FIRST"
                break
            if liquidation >= target:
                exit_tick, label = tick, "TP_FIRST"
                break
        else:
            if liquidation >= stop:
                exit_tick, label = tick, "SL_FIRST"
                break
            if liquidation <= target:
                exit_tick, label = tick, "TP_FIRST"
                break

    with localcontext() as context:
        context.prec = 50
        price_move = (
            exit_tick.bid - entry_tick.bid
            if decision.action == "buy"
            else entry_tick.bid - exit_tick.bid
        )
        gross = _money_from_points(source, price_move / source.tick_size)
        initial_risk = _money_from_points(source, risk_price / source.tick_size)
    return ClosedTrade(
        type="closed_trade",
        label=label,
        setup_id=decision.setup_id,
        evidence_ids=_record_evidence(source, policy, decision),
        formed_at_utc=decision.formed_at_utc,
        decision_available_at_utc=decision.confirmed_at_utc,
        decision_at_utc=decision_at,
        label_horizon_end_utc=scheduled_exit,
        outcome_available_at_utc=max(scheduled_exit, coverage.available_at_utc),
        entry_at_utc=entry_tick.event_time_utc,
        exit_at_utc=exit_tick.event_time_utc,
        filled_volume_lots=source.filled_volume_lots,
        point_value_per_lot=source.point_value_per_lot,
        initial_risk=initial_risk,
        gross_pnl=gross,
        swap_cost=source.swap_cost_per_trade,
        partial_deal_count=1,
    )


def build_bundle(source: PA01BacktestInput) -> ResearchBundle:
    try:
        checked = PA01BacktestInput.model_validate(source.model_dump())
        policies = {policy.m5_evidence_id: policy for policy in checked.policies}
        ticks = checked.ticks
        event_times = [tick.event_time_utc for tick in ticks]
        available_times = [tick.available_at_utc for tick in ticks]
        records: list[ClosedTrade | ExcludedRecord] = []
        side_by_setup: dict[str, Literal["buy", "sell"]] = {}
        trades: list[ClosedTrade] = []
        for bar in _eligible_m5(checked):
            policy = policies[bar.evidence_id]
            cutoff = bar.available_at_utc
            quote_index = bisect_right(available_times, cutoff) - 1
            if quote_index < 0:
                raise ValueError("decision quote unavailable")
            quote = ticks[quote_index]
            active = next(
                (
                    trade
                    for trade in trades
                    if trade.entry_at_utc <= cutoff < trade.exit_at_utc
                ),
                None,
            )
            context = PA01Context(
                cutoff_utc=cutoff,
                symbol=checked.symbol,
                feed_id=checked.feed_id,
                spread_price=quote.ask - quote.bid,
                market_open=policy.market_open,
                price_stale=(cutoff - quote.event_time_utc).total_seconds()
                > MAX_TICK_GAP_SECONDS,
                news_blocked=policy.news_blocked,
                has_exposure=active is not None,
                has_pending=False,
            )
            decision = evaluate_pa01(
                context,
                m5_bars=checked.m5_bars,
                h1_bars=checked.h1_bars,
            )
            if decision.action not in {"buy", "sell"}:
                records.append(
                    _excluded(
                        checked,
                        policy,
                        decision,
                        at=cutoff,
                        record_type="wait",
                        reason=decision.reason_code,
                    )
                )
                continue
            labelled = _label_trade(
                checked, policy, decision, cutoff, ticks, event_times
            )
            records.append(labelled)
            if isinstance(labelled, ClosedTrade):
                if any(
                    trade.entry_at_utc < labelled.exit_at_utc
                    and labelled.entry_at_utc < trade.exit_at_utc
                    for trade in trades
                ):
                    raise ValueError("overlapping replay exposure")
                side_by_setup[labelled.setup_id] = decision.action
                trades.append(labelled)

        if not trades or checked.bootstrap.block_length > len(trades):
            raise ValueError("insufficient closed-trade evidence")

        # Frozen Pydantic models cannot carry an unvalidated side field. Build the
        # mark-to-market path here with the separately retained deterministic map.
        equity = _equity_path_with_sides(checked, tuple(trades), side_by_setup)
        fields = {
            "protocol": BUNDLE_PROTOCOL,
            "strategy_version": checked.strategy_version,
            "strategy_code_hash": checked.strategy_code_hash,
            "split": checked.split,
            "data_cutoff_utc": checked.evaluation_window.end_utc,
            "evaluation_window": checked.evaluation_window,
            "cost_assumptions": checked.cost_assumptions,
            "bootstrap": checked.bootstrap,
            "initial_equity": checked.initial_equity,
            "equity_basis": "mark_to_market_including_open_exposure",
            "records": tuple(records),
            "equity_samples": equity,
        }
        unhashed = ResearchBundle.model_construct(dataset_hash="0" * 64, **fields)
        dataset_hash = hashlib.sha256(
            canonical(unhashed.model_dump(mode="json", exclude={"dataset_hash"})).encode()
        ).hexdigest()
        bundle = ResearchBundle.model_validate({**fields, "dataset_hash": dataset_hash})
        raw = canonical(bundle.model_dump(mode="json"))
        if len(raw.encode()) > MAX_BUNDLE_BYTES:
            raise ValueError("bundle exceeds evaluator boundary")
        if bundle_dict(raw)["dataset_hash"] != dataset_hash:
            raise ValueError("bundle self-check failed")
        return bundle
    except PA01BacktestInvalid:
        raise
    except (
        ResearchEvaluationInvalid,
        InvalidOperation,
        ArithmeticError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        ValidationError,
    ):
        raise PA01BacktestInvalid() from None


def _equity_path_with_sides(
    source: PA01BacktestInput,
    trades: tuple[ClosedTrade, ...],
    sides: dict[str, Literal["buy", "sell"]],
) -> tuple[EquitySample, ...]:
    window = source.evaluation_window
    by_entry = {trade.entry_at_utc: trade for trade in trades}
    by_exit = {trade.exit_at_utc: trade for trade in trades}
    samples = [
        EquitySample(
            event_time_utc=window.start_utc,
            available_at_utc=window.start_utc,
            equity=source.initial_equity,
            open_setup_ids=(),
        )
    ]
    realized = Decimal(0)
    active: ClosedTrade | None = None
    entry_bid: Decimal | None = None
    for tick in source.ticks:
        if not window.start_utc < tick.event_time_utc < window.end_utc:
            continue
        entering = by_entry.get(tick.event_time_utc)
        if entering is not None:
            if active is not None:
                raise PA01BacktestInvalid()
            active, entry_bid = entering, tick.bid
        exiting = by_exit.get(tick.event_time_utc)
        if exiting is not None:
            if active is None or active.setup_id != exiting.setup_id:
                raise PA01BacktestInvalid()
            realized += _net(source, exiting.gross_pnl)
            active, entry_bid = None, None
            samples.append(
                EquitySample(
                    event_time_utc=tick.event_time_utc,
                    available_at_utc=tick.available_at_utc,
                    equity=source.initial_equity + realized,
                    open_setup_ids=(),
                )
            )
        elif active is not None and entry_bid is not None:
            move = (
                tick.bid - entry_bid
                if sides[active.setup_id] == "buy"
                else entry_bid - tick.bid
            )
            gross = _money_from_points(source, move / source.tick_size)
            equity = source.initial_equity + realized + _net(source, gross)
            if equity <= 0:
                raise PA01BacktestInvalid()
            samples.append(
                EquitySample(
                    event_time_utc=tick.event_time_utc,
                    available_at_utc=tick.available_at_utc,
                    equity=equity,
                    open_setup_ids=(active.setup_id,),
                )
            )
    if active is not None:
        raise PA01BacktestInvalid()
    final = source.initial_equity + realized
    if final <= 0:
        raise PA01BacktestInvalid()
    samples.append(
        EquitySample(
            event_time_utc=window.end_utc,
            available_at_utc=window.end_utc,
            equity=final,
            open_setup_ids=(),
        )
    )
    return tuple(samples)


def write_bundle(path: Path, bundle: ResearchBundle) -> str:
    temporary: Path | None = None
    try:
        target = canonical_path(str(path))
        parent = target.parent
        metadata = parent.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            raise ValueError("private output directory required")
        raw = canonical(bundle.model_dump(mode="json")).encode()
        if len(raw) > MAX_BUNDLE_BYTES:
            raise ValueError("bundle too large")
        if target.exists():
            if private_bytes(target, MAX_BUNDLE_BYTES) == raw:
                return bundle.dataset_hash
            raise ValueError("output already exists with different evidence")
        suffix = hashlib.sha256(raw).hexdigest()[:16]
        temporary = parent / f".{target.name}.{suffix}.tmp"
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, target, follow_symlinks=False)
            os.unlink(temporary)
            temporary = None
            directory = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            with suppress(OSError):
                os.close(descriptor)
            raise
        return bundle.dataset_hash
    except (OSError, ValueError, TypeError, RecursionError, SyncConfigInvalid):
        if temporary is not None:
            with suppress(FileNotFoundError):
                temporary.unlink()
        raise PA01BacktestInvalid() from None
