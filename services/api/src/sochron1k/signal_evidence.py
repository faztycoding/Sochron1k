"""Bounded owner projection of synchronized, versioned signal evidence."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

import httpx
from pydantic import (
    AwareDatetime,
    Field,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from .bridge_api import unique_object
from .models import StrictModel
from .owner_auth import MAX_TOKEN, OwnerAuthSettings

MAX_SIGNALS = 50
MAX_EVIDENCE_IDS = 64
MAX_UPSTREAM_BYTES = 256 * 1024
SignalAction = Literal["buy", "sell", "wait", "block"]
ExperimentStatus = Literal["draft", "shadow", "demo", "halted", "closed", "archived"]
StrategyStatus = Literal["candidate", "approved", "active", "retired", "rejected"]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]

SIGNAL_SELECT = (
    "id,owner_id,signal_id,setup_id,action,formed_at,confirmed_at,expires_at,"
    "evidence_ids,blocked_reason,created_at,"
    "experiment:experiments!signals_owner_experiment_fkey("
    "owner_id,experiment_id,status,policy_version,started_at,ended_at),"
    "strategy:strategy_versions!signals_owner_strategy_fkey("
    "owner_id,version_id,code_hash,status,data_cutoff)"
)


class SignalEvidenceUnavailable(RuntimeError):
    pass


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _safe_text(value: str) -> str:
    has_control = any(ord(character) < 32 or ord(character) == 127 for character in value)
    if not value.strip() or has_control:
        raise ValueError("control or blank text is not allowed")
    return value


class SourceExperiment(StrictModel):
    owner_id: UUID
    experiment_id: Identifier
    status: ExperimentStatus
    policy_version: str = Field(min_length=1, max_length=64)
    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None

    @field_validator("experiment_id", "policy_version")
    @classmethod
    def safe_text(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("started_at", "ended_at")
    @classmethod
    def normalize_time(cls, value: datetime | None) -> datetime | None:
        return _utc(value) if value is not None else None

    @model_validator(mode="after")
    def valid_interval(self):
        if self.ended_at is not None and (
            self.started_at is None or self.ended_at < self.started_at
        ):
            raise ValueError("invalid experiment interval")
        return self


class SourceStrategy(StrictModel):
    owner_id: UUID
    version_id: str = Field(min_length=1, max_length=64)
    code_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: StrategyStatus
    data_cutoff: AwareDatetime

    @field_validator("version_id")
    @classmethod
    def safe_version(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("data_cutoff")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)


class SourceSignal(StrictModel):
    id: StrictInt = Field(gt=0)
    owner_id: UUID
    signal_id: Identifier
    setup_id: Identifier
    action: SignalAction
    formed_at: AwareDatetime
    confirmed_at: AwareDatetime
    expires_at: AwareDatetime
    evidence_ids: tuple[Identifier, ...] = Field(max_length=MAX_EVIDENCE_IDS)
    blocked_reason: str | None = Field(default=None, min_length=1, max_length=256)
    created_at: AwareDatetime
    experiment: SourceExperiment
    strategy: SourceStrategy

    @field_validator("signal_id", "setup_id")
    @classmethod
    def safe_identifiers(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("evidence_ids")
    @classmethod
    def unique_safe_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("duplicate evidence ID")
        return tuple(_safe_text(item) for item in value)

    @field_validator("blocked_reason")
    @classmethod
    def safe_reason(cls, value: str | None) -> str | None:
        return _safe_text(value) if value is not None else None

    @field_validator("formed_at", "confirmed_at", "expires_at", "created_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def evidence_is_causal(self):
        if not self.formed_at <= self.confirmed_at < self.expires_at:
            raise ValueError("invalid signal interval")
        if self.created_at < self.confirmed_at or self.strategy.data_cutoff > self.confirmed_at:
            raise ValueError("future evidence")
        if not (
            self.owner_id == self.experiment.owner_id == self.strategy.owner_id
        ):
            raise ValueError("mixed owner evidence")
        if self.action == "block" and self.blocked_reason is None:
            raise ValueError("block reason required")
        if self.action in {"buy", "sell"} and self.blocked_reason is not None:
            raise ValueError("trade action cannot carry a block reason")
        return self


class SignalExperiment(StrictModel):
    experiment_id: str
    status: ExperimentStatus
    policy_version: str


class SignalStrategy(StrictModel):
    version_id: str
    code_hash: str
    status: StrategyStatus
    data_cutoff_utc: AwareDatetime


class SignalEvidence(StrictModel):
    signal_id: str
    setup_id: str
    action: SignalAction
    formed_at_utc: AwareDatetime
    confirmed_at_utc: AwareDatetime
    expires_at_utc: AwareDatetime
    created_at_utc: AwareDatetime
    evidence_ids: tuple[str, ...]
    blocked_reason: str | None
    experiment: SignalExperiment
    strategy: SignalStrategy

    @classmethod
    def from_source(cls, source: SourceSignal) -> SignalEvidence:
        return cls(
            signal_id=source.signal_id,
            setup_id=source.setup_id,
            action=source.action,
            formed_at_utc=source.formed_at,
            confirmed_at_utc=source.confirmed_at,
            expires_at_utc=source.expires_at,
            created_at_utc=source.created_at,
            evidence_ids=source.evidence_ids,
            blocked_reason=source.blocked_reason,
            experiment=SignalExperiment(
                experiment_id=source.experiment.experiment_id,
                status=source.experiment.status,
                policy_version=source.experiment.policy_version,
            ),
            strategy=SignalStrategy(
                version_id=source.strategy.version_id,
                code_hash=source.strategy.code_hash,
                status=source.strategy.status,
                data_cutoff_utc=source.strategy.data_cutoff,
            ),
        )


class SignalEvidenceStatus(StrictModel):
    state: Literal["awaiting_source", "available"]
    returned_count: StrictInt = Field(ge=0, le=MAX_SIGNALS)
    limit: Literal[50] = MAX_SIGNALS
    auto_trading_enabled: Literal[False] = False
    execution_ready: Literal[False] = False


class SignalEvidenceView(StrictModel):
    trading_mode: Literal["demo"] = "demo"
    read_only: Literal[True] = True
    source: Literal["supabase-signals"] = "supabase-signals"
    read_at_utc: AwareDatetime
    status: SignalEvidenceStatus
    signals: tuple[SignalEvidence, ...] = ()


class SignalEvidenceReader:
    """Reads owner-RLS signal rows without privileged credentials or mutation authority."""

    def __init__(
        self,
        settings: OwnerAuthSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.settings = settings
        self._transport = transport
        self._now = now

    async def view(self, owner_id: UUID, authorization: list[str]) -> SignalEvidenceView:
        if (
            len(authorization) != 1
            or not authorization[0].startswith("Bearer ")
            or len(authorization[0]) > MAX_TOKEN + 7
        ):
            raise SignalEvidenceUnavailable()
        headers = {
            "Accept": "application/json",
            "apikey": self.settings.public_key.get_secret_value(),
            "Authorization": authorization[0],
        }
        params = {
            "select": SIGNAL_SELECT,
            "order": "confirmed_at.desc,id.desc",
            "limit": str(MAX_SIGNALS),
        }
        try:
            async with (
                asyncio.timeout(5),
                httpx.AsyncClient(
                    base_url=self.settings.supabase_url,
                    headers=headers,
                    timeout=2,
                    follow_redirects=False,
                    trust_env=False,
                    transport=self._transport,
                ) as client,
                client.stream("GET", "/rest/v1/signals", params=params) as response,
            ):
                if response.status_code != 200 or not response.headers.get(
                    "content-type", ""
                ).lower().startswith("application/json"):
                    raise SignalEvidenceUnavailable()
                payload = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(payload) + len(chunk) > MAX_UPSTREAM_BYTES:
                        raise SignalEvidenceUnavailable()
                    payload.extend(chunk)
        except httpx.HTTPError, TimeoutError:
            raise SignalEvidenceUnavailable() from None
        try:
            raw = json.loads(payload, object_pairs_hook=unique_object)
            if not isinstance(raw, list) or len(raw) > MAX_SIGNALS:
                raise SignalEvidenceUnavailable()
            rows = tuple(SourceSignal.model_validate(item) for item in raw)
        except (TypeError, ValueError, ValidationError, RecursionError):
            raise SignalEvidenceUnavailable() from None
        if any(row.owner_id != owner_id for row in rows):
            raise SignalEvidenceUnavailable()
        keys = [(row.confirmed_at, row.id) for row in rows]
        if keys != sorted(keys, reverse=True):
            raise SignalEvidenceUnavailable()
        if len({row.id for row in rows}) != len(rows) or len(
            {row.signal_id for row in rows}
        ) != len(rows):
            raise SignalEvidenceUnavailable()
        signals = tuple(SignalEvidence.from_source(row) for row in rows)
        return SignalEvidenceView(
            read_at_utc=_utc(self._now()),
            status=SignalEvidenceStatus(
                state="available" if signals else "awaiting_source",
                returned_count=len(signals),
            ),
            signals=signals,
        )
