"""Pure reproducible evaluation of one immutable closed-trade evidence bundle."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext
from itertools import pairwise
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    Field,
    StrictBool,
    StrictInt,
    TypeAdapter,
    ValidationError,
    field_serializer,
    field_validator,
    model_validator,
)
from sochron1k.models import StrictModel

from .native_source import _object
from .sync_config import private_bytes
from .sync_journal import canonical

BUNDLE_PROTOCOL = "sochron.research-bundle.v1"
ENVELOPE_PROTOCOL = "sochron.research-evaluation-envelope.v1"
MANIFEST_PROTOCOL = "sochron.research-evaluation-manifest.v1"
PRODUCER_REVISION = "SCN-029/research-evaluation-v1.0.0"
MAX_BUNDLE_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 100_000
MAX_EQUITY_SAMPLES = 1_000_000
MAX_EVIDENCE_IDS = 32
MAX_MONEY = Decimal("100000000000000")
MAX_POINTS = Decimal("1000000")
QUANTUM = Decimal("0.00000001")
HASH_PATTERN = r"^[0-9a-f]{64}$"
SAFE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"

EvaluationSplit = Literal["train", "validation", "test", "walk_forward", "shadow_demo"]
ExcludedType = Literal["wait", "rejected", "counterfactual", "ambiguous"]
TradeLabel = Literal["TP_FIRST", "SL_FIRST", "TIME_EXIT", "MANUAL_EXIT"]


class ResearchEvaluationInvalid(RuntimeError):
    def __init__(self) -> None:
        super().__init__("RESEARCH_EVALUATION_INVALID")


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _finite(value: Decimal) -> Decimal:
    if not value.is_finite() or abs(value) > MAX_MONEY:
        raise ValueError("finite bounded decimal required")
    return value


def _positive(value: Decimal) -> Decimal:
    value = _finite(value)
    if value <= 0:
        raise ValueError("positive decimal required")
    return value


def _safe_text(value: str) -> str:
    if not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("safe text required")
    return value


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _quantize(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("finite result required")
    return value.quantize(QUANTUM, rounding=ROUND_HALF_EVEN)


class ExactModel(StrictModel):
    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_exact(self, value):
        if isinstance(value, Decimal):
            return _decimal_text(value)
        if isinstance(value, datetime):
            return _utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")
        return value


class CostAssumptions(ExactModel):
    spread_points: Decimal = Field(ge=0, le=MAX_POINTS)
    slippage_points: Decimal = Field(ge=0, le=MAX_POINTS)
    commission_per_lot: Decimal = Field(ge=0, le=MAX_MONEY)
    swap_included: StrictBool
    operating_cost_per_trade: Decimal = Field(ge=0, le=MAX_MONEY)
    currency: str = Field(pattern=r"^[A-Z]{3}$")

    @field_validator(
        "spread_points", "slippage_points", "commission_per_lot", "operating_cost_per_trade"
    )
    @classmethod
    def finite_costs(cls, value: Decimal) -> Decimal:
        return _finite(value)


class BootstrapPlan(StrictModel):
    seed: StrictInt = Field(ge=1, le=9_223_372_036_854_775_807)
    samples: StrictInt = Field(ge=1_000, le=100_000)
    block_length: StrictInt = Field(ge=1, le=100_000)


class EvaluationWindow(ExactModel):
    start_utc: AwareDatetime
    end_utc: AwareDatetime
    prior_development_cutoff_utc: AwareDatetime | None
    embargo_seconds: StrictInt = Field(ge=0, le=31_536_000)

    @field_validator("start_utc", "end_utc", "prior_development_cutoff_utc")
    @classmethod
    def normalize_times(cls, value: datetime | None) -> datetime | None:
        return _utc(value) if value is not None else None

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end_utc <= self.start_utc:
            raise ValueError("evaluation window must be positive")
        return self


class RecordBase(ExactModel):
    setup_id: str = Field(pattern=SAFE_ID_PATTERN)
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=MAX_EVIDENCE_IDS)
    formed_at_utc: AwareDatetime
    decision_available_at_utc: AwareDatetime
    decision_at_utc: AwareDatetime
    label_horizon_end_utc: AwareDatetime
    outcome_available_at_utc: AwareDatetime

    @field_validator(
        "formed_at_utc",
        "decision_available_at_utc",
        "decision_at_utc",
        "label_horizon_end_utc",
        "outcome_available_at_utc",
    )
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _utc(value)

    @field_validator("evidence_ids")
    @classmethod
    def evidence_is_unique_and_safe(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value) or any(
            not item
            or len(item) > 128
            or any(ord(char) < 32 or ord(char) == 127 for char in item)
            for item in value
        ):
            raise ValueError("unique safe evidence IDs required")
        return value

    @model_validator(mode="after")
    def causal_decision(self) -> Self:
        if not (
            self.formed_at_utc
            <= self.decision_available_at_utc
            <= self.decision_at_utc
            <= self.label_horizon_end_utc
            <= self.outcome_available_at_utc
        ):
            raise ValueError("record timing is not causal")
        return self


class ClosedTrade(RecordBase):
    type: Literal["closed_trade"]
    label: TradeLabel
    entry_at_utc: AwareDatetime
    exit_at_utc: AwareDatetime
    filled_volume_lots: Decimal
    point_value_per_lot: Decimal
    initial_risk: Decimal
    gross_pnl: Decimal
    swap_cost: Decimal = Field(ge=0)
    partial_deal_count: StrictInt = Field(ge=1, le=10_000)

    @field_validator("entry_at_utc", "exit_at_utc")
    @classmethod
    def normalize_trade_times(cls, value: datetime) -> datetime:
        return _utc(value)

    @field_validator("filled_volume_lots", "point_value_per_lot", "initial_risk")
    @classmethod
    def positive_values(cls, value: Decimal) -> Decimal:
        return _positive(value)

    @field_validator("gross_pnl", "swap_cost")
    @classmethod
    def finite_values(cls, value: Decimal) -> Decimal:
        return _finite(value)

    @model_validator(mode="after")
    def valid_fill_lifecycle(self) -> Self:
        if not (
            self.decision_at_utc <= self.entry_at_utc <= self.exit_at_utc
            and self.exit_at_utc <= self.label_horizon_end_utc
        ):
            raise ValueError("trade lifecycle is not causal")
        return self


class ExcludedRecord(RecordBase):
    type: ExcludedType
    reason_code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")


ResearchRecord = Annotated[ClosedTrade | ExcludedRecord, Field(discriminator="type")]


class EquitySample(ExactModel):
    event_time_utc: AwareDatetime
    available_at_utc: AwareDatetime
    equity: Decimal
    open_setup_ids: tuple[str, ...] = Field(max_length=1_000)

    @field_validator("event_time_utc", "available_at_utc")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _utc(value)

    @field_validator("equity")
    @classmethod
    def positive_equity(cls, value: Decimal) -> Decimal:
        return _positive(value)

    @field_validator("open_setup_ids")
    @classmethod
    def unique_setup_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value) or any(
            not item
            or len(item) > 128
            or any(ord(char) < 32 or ord(char) == 127 for char in item)
            for item in value
        ):
            raise ValueError("unique safe open setup IDs required")
        return value

    @model_validator(mode="after")
    def causal_availability(self) -> Self:
        if self.available_at_utc < self.event_time_utc:
            raise ValueError("equity availability precedes event")
        return self


class ResearchBundle(ExactModel):
    protocol: Literal["sochron.research-bundle.v1"] = BUNDLE_PROTOCOL
    strategy_version: str = Field(min_length=1, max_length=64)
    strategy_code_hash: str = Field(pattern=HASH_PATTERN)
    dataset_hash: str = Field(pattern=HASH_PATTERN)
    split: EvaluationSplit
    data_cutoff_utc: AwareDatetime
    evaluation_window: EvaluationWindow
    cost_assumptions: CostAssumptions
    bootstrap: BootstrapPlan
    initial_equity: Decimal
    equity_basis: Literal["mark_to_market_including_open_exposure"]
    records: tuple[ResearchRecord, ...] = Field(min_length=1, max_length=MAX_RECORDS)
    equity_samples: tuple[EquitySample, ...] = Field(min_length=2, max_length=MAX_EQUITY_SAMPLES)

    @field_validator("strategy_version")
    @classmethod
    def safe_strategy_version(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("data_cutoff_utc")
    @classmethod
    def normalize_cutoff(cls, value: datetime) -> datetime:
        return _utc(value)

    @field_validator("initial_equity")
    @classmethod
    def positive_initial_equity(cls, value: Decimal) -> Decimal:
        return _positive(value)

    @model_validator(mode="after")
    def validate_bundle_relationships(self) -> Self:
        window = self.evaluation_window
        if self.data_cutoff_utc != window.end_utc:
            raise ValueError("data cutoff must equal evaluation-window end")
        if self.split == "train":
            if window.prior_development_cutoff_utc is not None or window.embargo_seconds != 0:
                raise ValueError("train split cannot claim prior-development embargo")
        else:
            prior = window.prior_development_cutoff_utc
            if (
                prior is None
                or prior + timedelta(seconds=window.embargo_seconds) > window.start_utc
            ):
                raise ValueError("non-train split requires a complete embargo")

        setup_ids = [record.setup_id for record in self.records]
        if len(set(setup_ids)) != len(setup_ids):
            raise ValueError("duplicate setup ID")
        evidence_ids = [item for record in self.records for item in record.evidence_ids]
        if len(set(evidence_ids)) != len(evidence_ids):
            raise ValueError("evidence ID reused across records")

        closed = {
            record.setup_id: record
            for record in self.records
            if isinstance(record, ClosedTrade)
        }
        if not closed or self.bootstrap.block_length > len(closed):
            raise ValueError("closed sample required and block length cannot exceed it")
        for record in self.records:
            if not (
                window.start_utc <= record.decision_at_utc
                and record.outcome_available_at_utc <= self.data_cutoff_utc
                and record.label_horizon_end_utc <= window.end_utc
            ):
                raise ValueError("record crosses evaluation window or cutoff")

        samples = self.equity_samples
        if (
            samples[0].event_time_utc != window.start_utc
            or samples[-1].event_time_utc != window.end_utc
        ):
            raise ValueError("equity path must cover the exact evaluation window")
        if samples[0].equity != self.initial_equity or samples[-1].open_setup_ids:
            raise ValueError("equity endpoints are inconsistent")
        if any(sample.available_at_utc > self.data_cutoff_utc for sample in samples):
            raise ValueError("future equity evidence")
        if any(
            later.event_time_utc <= earlier.event_time_utc
            for earlier, later in pairwise(samples)
        ):
            raise ValueError("equity path must be strictly ordered")

        seen_open: set[str] = set()
        for sample in samples:
            for setup_id in sample.open_setup_ids:
                trade = closed.get(setup_id)
                if trade is None or not (
                    trade.entry_at_utc <= sample.event_time_utc <= trade.exit_at_utc
                ):
                    raise ValueError("equity path references an invalid open setup")
                seen_open.add(setup_id)
        if seen_open != set(closed):
            raise ValueError("every closed trade needs an open-exposure equity mark")
        return self


class ResearchMetrics(ExactModel):
    sample_size: StrictInt = Field(ge=1)
    wins: StrictInt = Field(ge=0)
    losses: StrictInt = Field(ge=0)
    breakeven: StrictInt = Field(ge=0)
    net_return_pct: Decimal = Field(ge=-100)
    expectancy_r: Decimal
    expectancy_r_ci95_low: Decimal
    expectancy_r_ci95_high: Decimal
    max_drawdown_pct: Decimal = Field(ge=0, le=100)
    profit_factor: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def internally_consistent(self) -> Self:
        if self.wins + self.losses + self.breakeven != self.sample_size:
            raise ValueError("outcome counts do not equal sample size")
        if not self.expectancy_r_ci95_low <= self.expectancy_r <= self.expectancy_r_ci95_high:
            raise ValueError("expectancy lies outside interval")
        return self


class RecordCounts(StrictModel):
    closed_trade: StrictInt = Field(ge=1)
    wait: StrictInt = Field(ge=0)
    rejected: StrictInt = Field(ge=0)
    counterfactual: StrictInt = Field(ge=0)
    ambiguous: StrictInt = Field(ge=0)


class EvidenceManifest(ExactModel):
    manifest_protocol: Literal["sochron.research-evaluation-manifest.v1"] = MANIFEST_PROTOCOL
    bundle_hash: str = Field(pattern=HASH_PATTERN)
    strategy_version: str = Field(min_length=1, max_length=64)
    strategy_code_hash: str = Field(pattern=HASH_PATTERN)
    evaluation_window: EvaluationWindow
    bootstrap: BootstrapPlan
    record_counts: RecordCounts
    equity_basis: Literal["mark_to_market_including_open_exposure"]
    cost_currency: str = Field(pattern=r"^[A-Z]{3}$")


class ResearchEvaluationEnvelope(ExactModel):
    protocol: Literal["sochron.research-evaluation-envelope.v1"] = ENVELOPE_PROTOCOL
    producer_revision: Literal["SCN-029/research-evaluation-v1.0.0"] = PRODUCER_REVISION
    evaluation_fingerprint: str = Field(pattern=HASH_PATTERN)
    dataset_hash: str = Field(pattern=HASH_PATTERN)
    strategy_code_hash: str = Field(pattern=HASH_PATTERN)
    split: EvaluationSplit
    data_cutoff_utc: AwareDatetime
    metrics: ResearchMetrics
    cost_assumptions: CostAssumptions
    evidence_manifest: EvidenceManifest

    @field_validator("data_cutoff_utc")
    @classmethod
    def normalize_cutoff(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def matching_evidence(self) -> Self:
        manifest = self.evidence_manifest
        if (
            self.dataset_hash != manifest.bundle_hash
            or self.strategy_code_hash != manifest.strategy_code_hash
            or self.data_cutoff_utc != manifest.evaluation_window.end_utc
            or self.cost_assumptions.currency != manifest.cost_currency
        ):
            raise ValueError("envelope evidence mismatch")
        payload = self.model_dump(mode="json", exclude={"evaluation_fingerprint"})
        if hashlib.sha256(canonical(payload).encode()).hexdigest() != self.evaluation_fingerprint:
            raise ValueError("evaluation fingerprint mismatch")
        return self


_BUNDLE = TypeAdapter(ResearchBundle)
_ENVELOPE = TypeAdapter(ResearchEvaluationEnvelope)


def _reject_float(_: str):
    raise ValueError("decimal JSON values must be exact strings")


def _reject_constant(_: str):
    raise ValueError("non-finite JSON number")


def bundle_dict(raw: str) -> dict:
    if not isinstance(raw, str) or len(raw.encode()) > MAX_BUNDLE_BYTES:
        raise ValueError("invalid bundle size")
    value = json.loads(
        raw,
        object_pairs_hook=_object,
        parse_float=_reject_float,
        parse_constant=_reject_constant,
    )
    if not isinstance(value, dict) or canonical(value) != raw:
        raise ValueError("canonical JSON object required")
    costs = value.get("cost_assumptions")
    records = value.get("records")
    samples = value.get("equity_samples")
    if (
        not isinstance(costs, dict)
        or not isinstance(records, list)
        or not isinstance(samples, list)
        or not isinstance(value.get("initial_equity"), str)
        or any(
            not isinstance(costs.get(key), str)
            for key in (
                "spread_points",
                "slippage_points",
                "commission_per_lot",
                "operating_cost_per_trade",
            )
        )
        or any(
            not isinstance(record, dict)
            or (
                record.get("type") == "closed_trade"
                and any(
                    not isinstance(record.get(key), str)
                    for key in (
                        "filled_volume_lots",
                        "point_value_per_lot",
                        "initial_risk",
                        "gross_pnl",
                        "swap_cost",
                    )
                )
            )
            for record in records
        )
        or any(
            not isinstance(sample, dict) or not isinstance(sample.get("equity"), str)
            for sample in samples
        )
    ):
        raise ValueError("decimal evidence must use exact strings")
    supplied_hash = value.get("dataset_hash")
    if not isinstance(supplied_hash, str):
        raise ValueError("dataset hash required")
    hashed = dict(value)
    del hashed["dataset_hash"]
    if hashlib.sha256(canonical(hashed).encode()).hexdigest() != supplied_hash:
        raise ValueError("dataset hash mismatch")
    return value


def load_bundle(path: Path) -> ResearchBundle:
    try:
        raw = private_bytes(path, MAX_BUNDLE_BYTES).decode("utf-8")
        return _BUNDLE.validate_python(bundle_dict(raw))
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        ValidationError,
    ):
        raise ResearchEvaluationInvalid() from None


class _Generator:
    """Small pinned xorshift generator; bootstrap output does not depend on Python random."""

    def __init__(self, seed: int) -> None:
        self.state = seed & ((1 << 64) - 1)

    def index(self, upper: int) -> int:
        value = self.state
        value ^= value >> 12
        value ^= (value << 25) & ((1 << 64) - 1)
        value ^= value >> 27
        self.state = value & ((1 << 64) - 1)
        return ((self.state * 2_685_821_657_736_338_717) & ((1 << 64) - 1)) % upper


def _bootstrap_interval(
    values: tuple[Decimal, ...], plan: BootstrapPlan
) -> tuple[Decimal, Decimal]:
    generator = _Generator(plan.seed)
    size = len(values)
    means: list[Decimal] = []
    with localcontext() as context:
        context.prec = 50
        for _ in range(plan.samples):
            sample: list[Decimal] = []
            while len(sample) < size:
                start = generator.index(size)
                for offset in range(plan.block_length):
                    sample.append(values[(start + offset) % size])
                    if len(sample) == size:
                        break
            means.append(sum(sample, Decimal(0)) / Decimal(size))
    means.sort()
    low = means[(plan.samples - 1) * 25 // 1000]
    high = means[((plan.samples - 1) * 975 + 999) // 1000]
    point = sum(values, Decimal(0)) / Decimal(size)
    return _quantize(min(low, point)), _quantize(max(high, point))


def _maximum_drawdown(samples: tuple[EquitySample, ...]) -> Decimal:
    peak = samples[0].equity
    maximum = Decimal(0)
    with localcontext() as context:
        context.prec = 50
        for sample in samples:
            peak = max(peak, sample.equity)
            maximum = max(maximum, (peak - sample.equity) * Decimal(100) / peak)
    return _quantize(maximum)


def evaluate_bundle(bundle: ResearchBundle) -> ResearchEvaluationEnvelope:
    try:
        trades = tuple(record for record in bundle.records if isinstance(record, ClosedTrade))
        net_values: list[Decimal] = []
        r_values: list[Decimal] = []
        positive = Decimal(0)
        negative = Decimal(0)
        with localcontext() as context:
            context.prec = 50
            for trade in trades:
                costs = bundle.cost_assumptions
                spread = costs.spread_points * trade.point_value_per_lot * trade.filled_volume_lots
                slippage = (
                    costs.slippage_points * trade.point_value_per_lot * trade.filled_volume_lots
                )
                commission = costs.commission_per_lot * trade.filled_volume_lots
                operating = costs.operating_cost_per_trade
                if not costs.swap_included and trade.swap_cost != 0:
                    raise ValueError("swap cost present while excluded")
                net = trade.gross_pnl - spread - slippage - commission - trade.swap_cost - operating
                _finite(net)
                net_values.append(net)
                r_values.append(net / trade.initial_risk)
                if net > 0:
                    positive += net
                elif net < 0:
                    negative += net

            total_net = sum(net_values, Decimal(0))
            expected_final = bundle.initial_equity + total_net
            if expected_final <= 0 or bundle.equity_samples[-1].equity != expected_final:
                raise ValueError("final equity does not reconcile to net P/L")
            expectancy = _quantize(sum(r_values, Decimal(0)) / Decimal(len(r_values)))
            low, high = _bootstrap_interval(tuple(r_values), bundle.bootstrap)
            net_return = _quantize(total_net * Decimal(100) / bundle.initial_equity)
            profit_factor = _quantize(positive / abs(negative)) if negative else None

        wins = sum(value > 0 for value in net_values)
        losses = sum(value < 0 for value in net_values)
        breakeven = len(net_values) - wins - losses
        metrics = ResearchMetrics(
            sample_size=len(trades),
            wins=wins,
            losses=losses,
            breakeven=breakeven,
            net_return_pct=net_return,
            expectancy_r=expectancy,
            expectancy_r_ci95_low=low,
            expectancy_r_ci95_high=high,
            max_drawdown_pct=_maximum_drawdown(bundle.equity_samples),
            profit_factor=profit_factor,
        )
        counts = Counter(record.type for record in bundle.records)
        manifest = EvidenceManifest(
            bundle_hash=bundle.dataset_hash,
            strategy_version=bundle.strategy_version,
            strategy_code_hash=bundle.strategy_code_hash,
            evaluation_window=bundle.evaluation_window,
            bootstrap=bundle.bootstrap,
            record_counts=RecordCounts(
                closed_trade=counts["closed_trade"],
                wait=counts["wait"],
                rejected=counts["rejected"],
                counterfactual=counts["counterfactual"],
                ambiguous=counts["ambiguous"],
            ),
            equity_basis=bundle.equity_basis,
            cost_currency=bundle.cost_assumptions.currency,
        )
        fields = {
            "protocol": ENVELOPE_PROTOCOL,
            "producer_revision": PRODUCER_REVISION,
            "dataset_hash": bundle.dataset_hash,
            "strategy_code_hash": bundle.strategy_code_hash,
            "split": bundle.split,
            "data_cutoff_utc": bundle.data_cutoff_utc,
            "metrics": metrics,
            "cost_assumptions": bundle.cost_assumptions,
            "evidence_manifest": manifest,
        }
        envelope = ResearchEvaluationEnvelope.model_validate(
            {
                **fields,
                "evaluation_fingerprint": hashlib.sha256(
                    canonical(
                        ResearchEvaluationEnvelope.model_construct(
                            evaluation_fingerprint="0" * 64, **fields
                        ).model_dump(mode="json", exclude={"evaluation_fingerprint"})
                    ).encode()
                ).hexdigest(),
            }
        )
        return envelope
    except (
        InvalidOperation,
        ArithmeticError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        ValidationError,
    ):
        raise ResearchEvaluationInvalid() from None


def decode_envelope(raw: str) -> ResearchEvaluationEnvelope:
    try:
        if not isinstance(raw, str) or len(raw.encode()) > 262_144:
            raise ValueError("invalid envelope")
        value = json.loads(raw, object_pairs_hook=_object, parse_constant=_reject_constant)
        envelope = _ENVELOPE.validate_python(value)
        if canonical(envelope.model_dump(mode="json")) != raw:
            raise ValueError("noncanonical envelope")
        return envelope
    except (ValueError, TypeError, KeyError, RecursionError, ValidationError):
        raise ResearchEvaluationInvalid() from None
