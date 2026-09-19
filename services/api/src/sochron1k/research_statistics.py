"""Bounded owner projection of versioned research evaluation evidence."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

import httpx
from pydantic import (
    AwareDatetime,
    Field,
    StrictBool,
    StrictInt,
    ValidationError,
    field_validator,
    model_validator,
)

from .bridge_api import unique_object
from .models import StrictModel
from .owner_auth import MAX_TOKEN, OwnerAuthSettings

MAX_EVALUATIONS = 30
MAX_UPSTREAM_BYTES = 256 * 1024
MAX_COUNT = 10_000_000
MAX_METRIC = Decimal("1000000")
EvaluationSplit = Literal["train", "validation", "test", "walk_forward", "shadow_demo"]
ExperimentStatus = Literal["draft", "shadow", "demo", "halted", "closed", "archived"]
StrategyStatus = Literal["candidate", "approved", "active", "retired", "rejected"]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]

EVALUATION_SELECT = (
    "id,owner_id,dataset_hash,split,metrics,cost_assumptions,data_cutoff,created_at,"
    "strategy:strategy_versions!evaluations_owner_strategy_fkey("
    "owner_id,version_id,code_hash,status,data_cutoff),"
    "experiment:experiments!evaluations_owner_experiment_fkey("
    "owner_id,experiment_id,status,policy_version)"
)


class ResearchStatisticsUnavailable(RuntimeError):
    pass


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _safe_text(value: str) -> str:
    has_control = any(ord(character) < 32 or ord(character) == 127 for character in value)
    if not value.strip() or has_control:
        raise ValueError("control or blank text is not allowed")
    return value


def _finite(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("metric must be finite")
    return value


def _reject_constant(_: str):
    raise ValueError("non-finite JSON number")


class SourceMetrics(StrictModel):
    sample_size: StrictInt = Field(ge=1, le=MAX_COUNT)
    wins: StrictInt = Field(ge=0, le=MAX_COUNT)
    losses: StrictInt = Field(ge=0, le=MAX_COUNT)
    breakeven: StrictInt = Field(ge=0, le=MAX_COUNT)
    net_return_pct: Decimal = Field(ge=-100, le=MAX_METRIC)
    expectancy_r: Decimal = Field(ge=-MAX_METRIC, le=MAX_METRIC)
    expectancy_r_ci95_low: Decimal = Field(ge=-MAX_METRIC, le=MAX_METRIC)
    expectancy_r_ci95_high: Decimal = Field(ge=-MAX_METRIC, le=MAX_METRIC)
    max_drawdown_pct: Decimal = Field(ge=0, le=100)
    profit_factor: Decimal | None = Field(default=None, ge=0, le=MAX_METRIC)

    @field_validator(
        "net_return_pct",
        "expectancy_r",
        "expectancy_r_ci95_low",
        "expectancy_r_ci95_high",
        "max_drawdown_pct",
        "profit_factor",
    )
    @classmethod
    def finite_metrics(cls, value: Decimal | None) -> Decimal | None:
        return _finite(value) if value is not None else None

    @model_validator(mode="after")
    def consistent_counts_and_interval(self):
        if self.wins + self.losses + self.breakeven != self.sample_size:
            raise ValueError("sample size does not match outcomes")
        if not self.expectancy_r_ci95_low <= self.expectancy_r <= self.expectancy_r_ci95_high:
            raise ValueError("expectancy lies outside its interval")
        return self


class SourceCosts(StrictModel):
    spread_points: Decimal = Field(ge=0, le=MAX_METRIC)
    slippage_points: Decimal = Field(ge=0, le=MAX_METRIC)
    commission_per_lot: Decimal = Field(ge=0, le=MAX_METRIC)
    swap_included: StrictBool
    operating_cost_per_trade: Decimal = Field(ge=0, le=MAX_METRIC)
    currency: str = Field(pattern=r"^[A-Z]{3}$")

    @field_validator(
        "spread_points", "slippage_points", "commission_per_lot", "operating_cost_per_trade"
    )
    @classmethod
    def finite_costs(cls, value: Decimal) -> Decimal:
        return _finite(value)


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


class SourceExperiment(StrictModel):
    owner_id: UUID
    experiment_id: Identifier
    status: ExperimentStatus
    policy_version: str = Field(min_length=1, max_length=64)

    @field_validator("experiment_id", "policy_version")
    @classmethod
    def safe_text(cls, value: str) -> str:
        return _safe_text(value)


class SourceEvaluation(StrictModel):
    id: StrictInt = Field(gt=0)
    owner_id: UUID
    dataset_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    split: EvaluationSplit
    metrics: SourceMetrics
    cost_assumptions: SourceCosts
    data_cutoff: AwareDatetime
    created_at: AwareDatetime
    strategy: SourceStrategy
    experiment: SourceExperiment | None

    @field_validator("data_cutoff", "created_at")
    @classmethod
    def normalize_times(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def causal_and_owner_scoped(self):
        if self.created_at < self.data_cutoff or self.strategy.data_cutoff > self.data_cutoff:
            raise ValueError("future evaluation evidence")
        if self.owner_id != self.strategy.owner_id:
            raise ValueError("mixed owner strategy")
        if self.experiment is not None and self.owner_id != self.experiment.owner_id:
            raise ValueError("mixed owner experiment")
        return self


class ResearchMetrics(StrictModel):
    sample_size: int
    wins: int
    losses: int
    breakeven: int
    win_rate_pct: Decimal
    net_return_pct: Decimal
    expectancy_r: Decimal
    expectancy_r_ci95_low: Decimal
    expectancy_r_ci95_high: Decimal
    max_drawdown_pct: Decimal
    profit_factor: Decimal | None


class ResearchCosts(StrictModel):
    spread_points: Decimal
    slippage_points: Decimal
    commission_per_lot: Decimal
    swap_included: bool
    operating_cost_per_trade: Decimal
    currency: str


class ResearchStrategy(StrictModel):
    version_id: str
    code_hash: str
    status: StrategyStatus
    data_cutoff_utc: AwareDatetime


class ResearchExperiment(StrictModel):
    experiment_id: str
    status: ExperimentStatus
    policy_version: str


class ResearchEvaluation(StrictModel):
    dataset_hash: str
    split: EvaluationSplit
    data_cutoff_utc: AwareDatetime
    created_at_utc: AwareDatetime
    metrics: ResearchMetrics
    cost_assumptions: ResearchCosts
    strategy: ResearchStrategy
    experiment: ResearchExperiment | None

    @classmethod
    def from_source(cls, source: SourceEvaluation) -> ResearchEvaluation:
        metrics = source.metrics
        win_rate = (Decimal(metrics.wins) * 100 / Decimal(metrics.sample_size)).quantize(
            Decimal("0.0001")
        )
        return cls(
            dataset_hash=source.dataset_hash,
            split=source.split,
            data_cutoff_utc=source.data_cutoff,
            created_at_utc=source.created_at,
            metrics=ResearchMetrics(
                sample_size=metrics.sample_size,
                wins=metrics.wins,
                losses=metrics.losses,
                breakeven=metrics.breakeven,
                win_rate_pct=win_rate,
                net_return_pct=metrics.net_return_pct,
                expectancy_r=metrics.expectancy_r,
                expectancy_r_ci95_low=metrics.expectancy_r_ci95_low,
                expectancy_r_ci95_high=metrics.expectancy_r_ci95_high,
                max_drawdown_pct=metrics.max_drawdown_pct,
                profit_factor=metrics.profit_factor,
            ),
            cost_assumptions=ResearchCosts.model_validate(
                source.cost_assumptions.model_dump()
            ),
            strategy=ResearchStrategy(
                version_id=source.strategy.version_id,
                code_hash=source.strategy.code_hash,
                status=source.strategy.status,
                data_cutoff_utc=source.strategy.data_cutoff,
            ),
            experiment=(
                ResearchExperiment(
                    experiment_id=source.experiment.experiment_id,
                    status=source.experiment.status,
                    policy_version=source.experiment.policy_version,
                )
                if source.experiment is not None
                else None
            ),
        )


class ResearchStatisticsStatus(StrictModel):
    state: Literal["awaiting_source", "available"]
    returned_count: StrictInt = Field(ge=0, le=MAX_EVALUATIONS)
    limit: Literal[30] = MAX_EVALUATIONS
    auto_trading_enabled: Literal[False] = False
    execution_ready: Literal[False] = False
    promotion_decided: Literal[False] = False


class ResearchStatisticsView(StrictModel):
    trading_mode: Literal["demo"] = "demo"
    read_only: Literal[True] = True
    source: Literal["supabase-evaluations"] = "supabase-evaluations"
    read_at_utc: AwareDatetime
    status: ResearchStatisticsStatus
    evaluations: tuple[ResearchEvaluation, ...] = ()


class ResearchStatisticsReader:
    """Reads owner-RLS evaluations without privileged credentials or mutation authority."""

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

    async def view(self, owner_id: UUID, authorization: list[str]) -> ResearchStatisticsView:
        if (
            len(authorization) != 1
            or not authorization[0].startswith("Bearer ")
            or len(authorization[0]) > MAX_TOKEN + 7
        ):
            raise ResearchStatisticsUnavailable()
        headers = {
            "Accept": "application/json",
            "apikey": self.settings.public_key.get_secret_value(),
            "Authorization": authorization[0],
        }
        params = {
            "select": EVALUATION_SELECT,
            "order": "created_at.desc,id.desc",
            "limit": str(MAX_EVALUATIONS),
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
                client.stream("GET", "/rest/v1/evaluations", params=params) as response,
            ):
                if response.status_code != 200 or not response.headers.get(
                    "content-type", ""
                ).lower().startswith("application/json"):
                    raise ResearchStatisticsUnavailable()
                payload = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(payload) + len(chunk) > MAX_UPSTREAM_BYTES:
                        raise ResearchStatisticsUnavailable()
                    payload.extend(chunk)
        except httpx.HTTPError, TimeoutError:
            raise ResearchStatisticsUnavailable() from None
        try:
            raw = json.loads(
                payload,
                object_pairs_hook=unique_object,
                parse_float=Decimal,
                parse_constant=_reject_constant,
            )
            if not isinstance(raw, list) or len(raw) > MAX_EVALUATIONS:
                raise ResearchStatisticsUnavailable()
            rows = tuple(SourceEvaluation.model_validate(item) for item in raw)
        except (TypeError, ValueError, ValidationError, RecursionError):
            raise ResearchStatisticsUnavailable() from None
        if any(row.owner_id != owner_id for row in rows):
            raise ResearchStatisticsUnavailable()
        keys = [(row.created_at, row.id) for row in rows]
        if keys != sorted(keys, reverse=True):
            raise ResearchStatisticsUnavailable()
        identities = {
            (row.strategy.version_id, row.dataset_hash, row.split, row.data_cutoff)
            for row in rows
        }
        if len({row.id for row in rows}) != len(rows) or len(identities) != len(rows):
            raise ResearchStatisticsUnavailable()
        evaluations = tuple(ResearchEvaluation.from_source(row) for row in rows)
        return ResearchStatisticsView(
            read_at_utc=_utc(self._now()),
            status=ResearchStatisticsStatus(
                state="available" if evaluations else "awaiting_source",
                returned_count=len(evaluations),
            ),
            evaluations=evaluations,
        )
