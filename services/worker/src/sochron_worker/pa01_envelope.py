"""Deterministic PA01 evidence envelope; no I/O, risk or execution authority."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal, Self

from pydantic import (
    AwareDatetime,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)
from sochron1k.models import StrictModel
from sochron1k.telemetry import FiniteDecimal

from .pa01 import (
    PARAMETER_HASH,
    PARAMETER_VERSION,
    DecisionAction,
    PA01Context,
    PA01ExecutionParameters,
    PA01Features,
    ReasonCode,
    evaluate_pa01,
)
from .pa01_aggregation import AGGREGATION_VERSION, PA01Aggregation

PROTOCOL = "sochron.pa01.decision.v2"
FEATURE_SCHEMA = "sochron.pa01.features.v1"
POLICY_SCHEMA = "sochron.pa01.policy-context.v1"
PRODUCER_REVISION = f"{PARAMETER_VERSION}/{AGGREGATION_VERSION}"
MAX_QUOTE_AGE_SECONDS = 5


class EnvelopeUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("PA01_ENVELOPE_UNAVAILABLE")


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _safe_text(value: str) -> str:
    if not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("unsafe text")
    return value


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class PolicyObservation(StrictModel):
    evidence_id: str = Field(min_length=1, max_length=128)
    observed_at_utc: AwareDatetime

    @field_validator("evidence_id")
    @classmethod
    def safe_evidence_id(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)


class PA01PolicyObservations(StrictModel):
    quote: PolicyObservation
    market: PolicyObservation
    news: PolicyObservation
    account: PolicyObservation


class PA01PolicyEvidence(StrictModel):
    cutoff_utc: AwareDatetime
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[^\s]+$")
    feed_id: str = Field(min_length=1, max_length=128)
    spread_price: FiniteDecimal = Field(ge=0)
    market_open: StrictBool
    price_stale: StrictBool
    news_blocked: StrictBool
    has_exposure: StrictBool
    has_pending: StrictBool
    ai_enabled: Literal[False] = False
    observations: PA01PolicyObservations

    @field_validator("spread_price", mode="before")
    @classmethod
    def exact_spread(cls, value: object) -> object:
        if not isinstance(value, Decimal):
            raise ValueError("Decimal spread required")
        return value

    @field_validator("cutoff_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)

    @field_validator("feed_id")
    @classmethod
    def safe_feed(cls, value: str) -> str:
        return _safe_text(value)

    @model_validator(mode="after")
    def causal_observations(self) -> Self:
        items = (
            self.observations.quote,
            self.observations.market,
            self.observations.news,
            self.observations.account,
        )
        if (
            len({item.evidence_id for item in items}) != len(items)
            or any(item.observed_at_utc > self.cutoff_utc for item in items)
            or (
                self.market_open
                and not self.price_stale
                and self.cutoff_utc - self.observations.quote.observed_at_utc
                > timedelta(seconds=MAX_QUOTE_AGE_SECONDS)
            )
        ):
            raise ValueError("invalid policy observations")
        return self

    def as_context(self) -> PA01Context:
        return PA01Context(
            cutoff_utc=self.cutoff_utc,
            symbol=self.symbol,
            feed_id=self.feed_id,
            spread_price=self.spread_price,
            market_open=self.market_open,
            price_stale=self.price_stale,
            news_blocked=self.news_blocked,
            has_exposure=self.has_exposure,
            has_pending=self.has_pending,
            ai_enabled=self.ai_enabled,
        )


class PA01StoredPolicyContext(StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )

    schema_id: Literal["sochron.pa01.policy-context.v1"] = Field(
        default=POLICY_SCHEMA, validation_alias="schema", serialization_alias="schema"
    )
    evidence_id: str = Field(min_length=1, max_length=128)
    kernel_decision_id: str = Field(min_length=1, max_length=128)
    market_data_cutoff_utc: AwareDatetime
    context_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    cutoff_utc: AwareDatetime
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[^\s]+$")
    feed_id: str = Field(min_length=1, max_length=128)
    spread_price: FiniteDecimal = Field(ge=0)
    market_open: StrictBool
    price_stale: StrictBool
    news_blocked: StrictBool
    has_exposure: StrictBool
    has_pending: StrictBool
    ai_enabled: Literal[False] = False
    observations: PA01PolicyObservations

    @field_validator("spread_price", mode="before")
    @classmethod
    def exact_spread(cls, value: object) -> object:
        if not isinstance(value, Decimal):
            raise ValueError("Decimal spread required")
        return value

    @field_validator("market_data_cutoff_utc", "cutoff_utc")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _utc(value)

    @field_validator("evidence_id", "kernel_decision_id", "feed_id")
    @classmethod
    def safe_identifiers(cls, value: str) -> str:
        return _safe_text(value)

    @model_validator(mode="after")
    def exact_context_identity(self) -> Self:
        source = PA01PolicyEvidence(
            cutoff_utc=self.cutoff_utc,
            symbol=self.symbol,
            feed_id=self.feed_id,
            spread_price=self.spread_price,
            market_open=self.market_open,
            price_stale=self.price_stale,
            news_blocked=self.news_blocked,
            has_exposure=self.has_exposure,
            has_pending=self.has_pending,
            ai_enabled=self.ai_enabled,
            observations=self.observations,
        )
        expected = _digest(source.model_dump(mode="json"))
        if (
            self.market_data_cutoff_utc > self.cutoff_utc
            or self.context_hash != expected
            or self.evidence_id != f"pa01-policy:{expected[:32]}"
        ):
            raise ValueError("invalid stored policy context")
        return self


class PA01SnapshotValues(StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )

    schema_id: Literal["sochron.pa01.features.v1"] = Field(
        default=FEATURE_SCHEMA, validation_alias="schema", serialization_alias="schema"
    )
    decision_id: str = Field(min_length=1, max_length=128)
    strategy_version: Literal["PA01-v1"] = "PA01-v1"
    code_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    parameter_version: Literal["PA01-v1.0.1"] = PARAMETER_VERSION
    parameter_hash: Literal["62c226e9eb3aefc003f122ac2e072dc335b293dc77bfbf3cde4b6e572e84e822"] = (
        PARAMETER_HASH
    )
    aggregation_version: Literal["native-pa01-aggregation-v1"] = AGGREGATION_VERSION
    aggregation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_dataset_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    data_cutoff_utc: AwareDatetime
    ai_enabled: Literal[False] = False
    action: DecisionAction
    reason_code: ReasonCode
    blocked_reason: str | None = Field(default=None, min_length=1, max_length=128)
    features: PA01Features
    execution_parameters: PA01ExecutionParameters

    @field_validator("decision_id")
    @classmethod
    def safe_decision_id(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("data_cutoff_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def action_semantics(self) -> Self:
        if (self.action == "block") != (self.blocked_reason is not None) or (
            self.action in {"buy", "sell"}
        ) != (self.reason_code == "SETUP_CONFIRMED"):
            raise ValueError("invalid decision semantics")
        return self


class PA01EnvelopeSnapshot(StrictModel):
    snapshot_id: str = Field(min_length=1, max_length=128)
    feed_id: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[^\s]+$")
    timeframe: Literal["M5"] = "M5"
    event_time: AwareDatetime
    received_at: AwareDatetime
    available_at: AwareDatetime
    dataset_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    values: PA01SnapshotValues
    decision_protocol: Literal["sochron.pa01.decision.v2"] = PROTOCOL
    policy_context: PA01StoredPolicyContext

    @field_validator("snapshot_id", "feed_id")
    @classmethod
    def safe_identifiers(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("event_time", "received_at", "available_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def linked_evidence(self) -> Self:
        if not (
            self.received_at
            == self.available_at
            == self.values.data_cutoff_utc
            == self.policy_context.cutoff_utc
            and self.dataset_hash == self.values.dataset_hash
            and self.feed_id == self.policy_context.feed_id
            and self.symbol == self.policy_context.symbol
            and self.event_time <= self.available_at
        ):
            raise ValueError("inconsistent snapshot evidence")
        return self


class PA01EnvelopeSignal(StrictModel):
    signal_id: str = Field(min_length=1, max_length=128)
    setup_id: str = Field(min_length=1, max_length=128)
    action: DecisionAction
    formed_at: AwareDatetime
    confirmed_at: AwareDatetime
    expires_at: AwareDatetime
    evidence_ids: tuple[str, ...] = Field(min_length=1, max_length=8)
    blocked_reason: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("signal_id", "setup_id")
    @classmethod
    def safe_identifiers(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("evidence_ids")
    @classmethod
    def safe_unique_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("duplicate evidence ID")
        return tuple(_safe_text(item) for item in value)

    @field_validator("formed_at", "confirmed_at", "expires_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def causal_signal(self) -> Self:
        if (
            not self.formed_at <= self.confirmed_at
            or self.expires_at != self.confirmed_at + timedelta(seconds=30)
            or (self.action == "block") != (self.blocked_reason is not None)
        ):
            raise ValueError("invalid signal evidence")
        return self


class PA01DecisionEnvelope(StrictModel):
    protocol: Literal["sochron.pa01.decision.v2"] = PROTOCOL
    producer_revision: Literal["PA01-v1.0.1/native-pa01-aggregation-v1"] = PRODUCER_REVISION
    decision_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot: PA01EnvelopeSnapshot
    signal: PA01EnvelopeSignal

    @model_validator(mode="after")
    def exact_links(self) -> Self:
        if not (
            self.snapshot.values.decision_id == self.signal.signal_id
            and self.snapshot.event_time == self.signal.formed_at
            and self.snapshot.available_at == self.signal.confirmed_at
            and self.snapshot.values.action == self.signal.action
            and self.snapshot.values.blocked_reason == self.signal.blocked_reason
            and self.snapshot.policy_context.evidence_id in self.signal.evidence_ids
        ):
            raise ValueError("inconsistent decision envelope")
        return self


def _expected_aggregation_hash(value: PA01Aggregation) -> str:
    return _digest(
        {
            "aggregation_version": value.aggregation_version,
            "cutoff_utc": value.cutoff_utc.isoformat(),
            "source_dataset_hash": value.source_dataset_hash,
            "m5": [bar.model_dump(mode="json") for bar in value.m5_bars],
            "h1": [bar.model_dump(mode="json") for bar in value.h1_bars],
        }
    )


def build_pa01_decision_envelope(
    aggregation: PA01Aggregation,
    policy: PA01PolicyEvidence,
    *,
    code_hash: str,
) -> PA01DecisionEnvelope:
    """Recompute PA01 and return one canonical protocol-v2 receiver payload."""
    try:
        if not isinstance(aggregation, PA01Aggregation) or not isinstance(
            policy, PA01PolicyEvidence
        ):
            raise EnvelopeUnavailable()
        checked_aggregation = PA01Aggregation.model_validate(aggregation.model_dump())
        checked_policy = PA01PolicyEvidence.model_validate(policy.model_dump())
        if (
            not isinstance(code_hash, str)
            or len(code_hash) != 64
            or any(char not in "0123456789abcdef" for char in code_hash)
            or checked_aggregation.aggregation_hash
            != _expected_aggregation_hash(checked_aggregation)
            or checked_aggregation.cutoff_utc != checked_policy.cutoff_utc
            or checked_aggregation.symbol != checked_policy.symbol
            or checked_aggregation.feed_id != checked_policy.feed_id
        ):
            raise EnvelopeUnavailable()

        decision = evaluate_pa01(
            checked_policy.as_context(),
            m5_bars=checked_aggregation.m5_bars,
            h1_bars=checked_aggregation.h1_bars,
        )
        policy_hash = _digest(checked_policy.model_dump(mode="json"))
        stored_policy = PA01StoredPolicyContext(
            evidence_id=f"pa01-policy:{policy_hash[:32]}",
            kernel_decision_id=decision.decision_id,
            market_data_cutoff_utc=decision.data_cutoff_utc,
            context_hash=policy_hash,
            **checked_policy.model_dump(),
        )
        fingerprint = _digest(
            {
                "protocol": PROTOCOL,
                "producer_revision": PRODUCER_REVISION,
                "code_hash": code_hash,
                "aggregation_version": checked_aggregation.aggregation_version,
                "aggregation_hash": checked_aggregation.aggregation_hash,
                "source_dataset_hash": checked_aggregation.source_dataset_hash,
                "policy_context": stored_policy.model_dump(mode="json"),
                "kernel_decision": decision.model_dump(mode="json"),
            }
        )
        signal_id = f"decision-pa01-{fingerprint[:32]}"
        snapshot_id = f"snapshot-pa01-{fingerprint[:32]}"
        evidence_ids = tuple(dict.fromkeys((*decision.evidence_ids, stored_policy.evidence_id)))
        values = PA01SnapshotValues(
            decision_id=signal_id,
            code_hash=code_hash,
            aggregation_hash=checked_aggregation.aggregation_hash,
            source_dataset_hash=checked_aggregation.source_dataset_hash,
            dataset_hash=decision.dataset_hash,
            data_cutoff_utc=checked_policy.cutoff_utc,
            action=decision.action,
            reason_code=decision.reason_code,
            blocked_reason=decision.blocked_reason,
            features=decision.features,
            execution_parameters=decision.execution_parameters,
        )
        snapshot = PA01EnvelopeSnapshot(
            snapshot_id=snapshot_id,
            feed_id=checked_policy.feed_id,
            symbol=checked_policy.symbol,
            event_time=decision.formed_at_utc,
            received_at=checked_policy.cutoff_utc,
            available_at=checked_policy.cutoff_utc,
            dataset_hash=decision.dataset_hash,
            values=values,
            policy_context=stored_policy,
        )
        signal = PA01EnvelopeSignal(
            signal_id=signal_id,
            setup_id=decision.setup_id,
            action=decision.action,
            formed_at=decision.formed_at_utc,
            confirmed_at=checked_policy.cutoff_utc,
            expires_at=checked_policy.cutoff_utc + timedelta(seconds=30),
            evidence_ids=evidence_ids,
            blocked_reason=decision.blocked_reason,
        )
        return PA01DecisionEnvelope(
            decision_fingerprint=fingerprint,
            snapshot=snapshot,
            signal=signal,
        )
    except EnvelopeUnavailable:
        raise
    except ValueError, TypeError, ArithmeticError, OverflowError, RecursionError:
        raise EnvelopeUnavailable() from None
