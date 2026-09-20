"""Provider-neutral, query-only API budget evidence for the Demo owner."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

from .models import StrictModel

MAX_PRIVATE_BYTES = 16_384
MAX_COST = Decimal("9999999999.99999999")
DECIMAL_PATTERN = re.compile(r"^(0|[1-9][0-9]{0,9})(\.[0-9]{1,8})?$")
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3,8}$")]
SafeText = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f]+$"),
]
BudgetState = Literal[
    "disabled",
    "awaiting_snapshot",
    "connected",
    "warning",
    "critical",
    "exhausted",
    "stale",
    "degraded",
]


class _InvalidBudgetSource(RuntimeError):
    pass


class _MissingBudgetSnapshot(FileNotFoundError):
    pass


def _decimal(value: object) -> Decimal:
    if isinstance(value, str) and DECIMAL_PATTERN.fullmatch(value):
        try:
            parsed = Decimal(value)
        except InvalidOperation:
            raise ValueError("canonical decimal required") from None
    else:
        raise ValueError("canonical decimal string required")
    if not parsed.is_finite() or parsed < 0 or parsed > MAX_COST:
        raise ValueError("bounded non-negative decimal required")
    return parsed


def _fraction(value: object) -> Decimal:
    parsed = _decimal(value)
    if not 0 < parsed <= 1:
        raise ValueError("fraction must be in (0, 1]")
    return parsed


class ApiBudgetSettings(StrictModel):
    snapshot_file: Path
    currency: Currency
    monthly_limit: Decimal
    warning_fraction: Decimal
    critical_fraction: Decimal
    stale_after_seconds: StrictInt = Field(ge=60, le=604_800)

    @field_validator("snapshot_file", mode="before")
    @classmethod
    def canonical_path(cls, value: object) -> Path:
        if not isinstance(value, (str, Path)) or not str(value) or "\x00" in str(value):
            raise ValueError("canonical path required")
        path = Path(value)
        if not path.is_absolute() or path.resolve() != path or str(path) != str(value):
            raise ValueError("canonical path required")
        return path

    @field_validator("monthly_limit", mode="before")
    @classmethod
    def positive_limit(cls, value: object) -> Decimal:
        parsed = _decimal(value)
        if parsed <= 0:
            raise ValueError("positive monthly limit required")
        return parsed

    @field_validator("warning_fraction", "critical_fraction", mode="before")
    @classmethod
    def exact_fraction(cls, value: object) -> Decimal:
        return _fraction(value)

    @model_validator(mode="after")
    def ordered_thresholds(self) -> Self:
        if self.warning_fraction >= self.critical_fraction:
            raise ValueError("warning threshold must precede critical threshold")
        return self


class ApiBudgetSnapshot(StrictModel):
    protocol: Literal["sochron.api-budget-snapshot.v1"]
    source_id: SafeText
    revision: SafeText
    period_start_utc: AwareDatetime
    period_end_utc: AwareDatetime
    observed_at_utc: AwareDatetime
    coverage_until_utc: AwareDatetime
    currency: Currency
    billed_cost: Decimal
    unbilled_estimate: Decimal

    @field_validator(
        "period_start_utc",
        "period_end_utc",
        "observed_at_utc",
        "coverage_until_utc",
    )
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @field_validator("billed_cost", "unbilled_estimate", mode="before")
    @classmethod
    def exact_cost(cls, value: object) -> Decimal:
        return _decimal(value)

    @model_validator(mode="after")
    def coherent_period(self) -> Self:
        duration = self.period_end_utc - self.period_start_utc
        if not timedelta(days=27) <= duration <= timedelta(days=32):
            raise ValueError("monthly billing period required")
        if not (
            self.period_start_utc
            <= self.coverage_until_utc
            <= self.observed_at_utc
            <= self.period_end_utc
        ):
            raise ValueError("incoherent budget evidence time")
        if self.billed_cost + self.unbilled_estimate > MAX_COST:
            raise ValueError("combined cost is too large")
        return self


class ApiBudgetPolicyView(StrictModel):
    currency: Currency
    monthly_limit: Decimal
    warning_fraction: Decimal
    critical_fraction: Decimal
    stale_after_seconds: StrictInt


class ApiBudgetEvidenceView(StrictModel):
    source_ref: str = Field(min_length=16, max_length=16, pattern=r"^[0-9a-f]{16}$")
    period_start_utc: AwareDatetime
    period_end_utc: AwareDatetime
    observed_at_utc: AwareDatetime
    coverage_until_utc: AwareDatetime
    billed_cost: Decimal
    unbilled_estimate: Decimal
    total_cost: Decimal
    remaining_amount: Decimal
    usage_percent: Decimal


class ApiBudgetView(StrictModel):
    protocol: Literal["sochron.api-budget-view.v1"] = "sochron.api-budget-view.v1"
    trading_mode: Literal["demo"] = "demo"
    read_only: Literal[True] = True
    auto_trading_enabled: Literal[False] = False
    execution_ready: Literal[False] = False
    state: BudgetState
    generated_at_utc: AwareDatetime
    policy: ApiBudgetPolicyView | None = None
    evidence: ApiBudgetEvidenceView | None = None

    @field_validator("generated_at_utc")
    @classmethod
    def normalize_generated_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def coherent_state(self) -> Self:
        configured = self.policy is not None
        has_evidence = self.evidence is not None
        if (self.state == "disabled") != (not configured):
            raise ValueError("incoherent budget configuration state")
        if self.state == "awaiting_snapshot" and has_evidence:
            raise ValueError("awaiting state cannot include evidence")
        if (
            self.state in {"connected", "warning", "critical", "exhausted", "stale"}
            and (not configured or not has_evidence)
        ):
            raise ValueError("budget evidence required")
        if self.state == "degraded" and not configured:
            raise ValueError("degraded source must be configured")
        return self


def _directory_identity(path: Path) -> tuple[int, int]:
    try:
        if not path.is_absolute() or path.resolve() != path:
            raise _InvalidBudgetSource()
        info = path.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise _InvalidBudgetSource()
        return info.st_dev, info.st_ino
    except OSError, ValueError, TypeError:
        raise _InvalidBudgetSource() from None


def _file_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _private_bytes(path: Path, *, missing_allowed: bool = False) -> bytes:
    parent = _directory_identity(path.parent)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        if missing_allowed:
            raise _MissingBudgetSnapshot() from None
        raise _InvalidBudgetSource() from None
    except OSError:
        raise _InvalidBudgetSource() from None
    try:
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) & 0o077
                or before.st_size > MAX_PRIVATE_BYTES
            ):
                raise _InvalidBudgetSource()
            raw = stream.read(MAX_PRIVATE_BYTES + 1)
            after = os.fstat(stream.fileno())
        current = path.lstat()
        if (
            len(raw) > MAX_PRIVATE_BYTES
            or _file_identity(before) != _file_identity(after)
            or _file_identity(after) != _file_identity(current)
            or _directory_identity(path.parent) != parent
        ):
            raise _InvalidBudgetSource()
        return raw
    except OSError, ValueError, TypeError:
        raise _InvalidBudgetSource() from None


def _json(raw: bytes) -> dict[str, object]:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    def reject_constant(_value: str) -> None:
        raise ValueError("non-finite JSON")

    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=unique,
        parse_float=Decimal,
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def load_api_budget_settings() -> ApiBudgetSettings | None:
    selected = os.environ.get("SOCHRON_API_BUDGET_CONFIG_FILE")
    if not selected:
        return None
    try:
        path = Path(selected)
        if not path.is_absolute() or path.resolve() != path or str(path) != selected:
            raise _InvalidBudgetSource()
        data = _json(_private_bytes(path))
        if set(data) == {"enabled"} and data["enabled"] is False:
            return None
        expected = set(ApiBudgetSettings.model_fields) | {"enabled"}
        if set(data) != expected or data.pop("enabled", None) is not True:
            raise _InvalidBudgetSource()
        settings = ApiBudgetSettings.model_validate(data)
        if path == settings.snapshot_file:
            raise _InvalidBudgetSource()
        _directory_identity(settings.snapshot_file.parent)
        return settings
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        _InvalidBudgetSource,
    ):
        raise RuntimeError(
            "Invalid private API budget configuration; source not started"
        ) from None


class ApiBudgetReader:
    """Validate one normalized provider-cost snapshot without mutating it."""

    def __init__(
        self,
        settings: ApiBudgetSettings | None,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.settings = settings
        self._utc_now = utc_now
        if settings is not None:
            try:
                self._snapshot_parent_identity = _directory_identity(
                    settings.snapshot_file.parent
                )
            except _InvalidBudgetSource:
                raise RuntimeError(
                    "Invalid private API budget configuration; source not started"
                ) from None

    def _now(self, supplied: datetime | None = None) -> datetime:
        value = supplied or self._utc_now()
        if value.tzinfo is None or value.utcoffset() is None:
            raise _InvalidBudgetSource()
        return value.astimezone(UTC)

    def _policy(self) -> ApiBudgetPolicyView:
        settings = self.settings
        if settings is None:
            raise _InvalidBudgetSource()
        return ApiBudgetPolicyView(
            currency=settings.currency,
            monthly_limit=settings.monthly_limit,
            warning_fraction=settings.warning_fraction,
            critical_fraction=settings.critical_fraction,
            stale_after_seconds=settings.stale_after_seconds,
        )

    def _evidence(self, snapshot: ApiBudgetSnapshot) -> ApiBudgetEvidenceView:
        settings = self.settings
        if settings is None:
            raise _InvalidBudgetSource()
        total = snapshot.billed_cost + snapshot.unbilled_estimate
        remaining = max(Decimal(0), settings.monthly_limit - total)
        usage_percent = (total * Decimal(100) / settings.monthly_limit).quantize(
            Decimal("0.0001"), rounding=ROUND_DOWN
        )
        return ApiBudgetEvidenceView(
            source_ref=hashlib.sha256(snapshot.source_id.encode()).hexdigest()[:16],
            period_start_utc=snapshot.period_start_utc,
            period_end_utc=snapshot.period_end_utc,
            observed_at_utc=snapshot.observed_at_utc,
            coverage_until_utc=snapshot.coverage_until_utc,
            billed_cost=snapshot.billed_cost,
            unbilled_estimate=snapshot.unbilled_estimate,
            total_cost=total,
            remaining_amount=remaining,
            usage_percent=usage_percent,
        )

    def view(self, now: datetime | None = None) -> ApiBudgetView:
        try:
            generated = self._now(now)
        except _InvalidBudgetSource:
            generated = datetime.now(UTC)
            if self.settings is None:
                return ApiBudgetView(state="disabled", generated_at_utc=generated)
            return ApiBudgetView(
                state="degraded", generated_at_utc=generated, policy=self._policy()
            )
        if self.settings is None:
            return ApiBudgetView(state="disabled", generated_at_utc=generated)
        policy = self._policy()
        try:
            if (
                _directory_identity(self.settings.snapshot_file.parent)
                != self._snapshot_parent_identity
            ):
                raise _InvalidBudgetSource()
            raw = _private_bytes(self.settings.snapshot_file, missing_allowed=True)
            snapshot = ApiBudgetSnapshot.model_validate(_json(raw))
            if snapshot.currency != self.settings.currency:
                raise _InvalidBudgetSource()
            evidence = self._evidence(snapshot)
        except _MissingBudgetSnapshot:
            return ApiBudgetView(
                state="awaiting_snapshot",
                generated_at_utc=generated,
                policy=policy,
            )
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            RecursionError,
            _InvalidBudgetSource,
        ):
            return ApiBudgetView(
                state="degraded", generated_at_utc=generated, policy=policy
            )

        if snapshot.observed_at_utc > generated or snapshot.coverage_until_utc > generated:
            state: BudgetState = "degraded"
        else:
            evidence_age = max(
                (generated - snapshot.observed_at_utc).total_seconds(),
                (generated - snapshot.coverage_until_utc).total_seconds(),
            )
            if (
                generated < snapshot.period_start_utc
                or generated >= snapshot.period_end_utc
                or evidence_age > self.settings.stale_after_seconds
            ):
                state = "stale"
            else:
                total = snapshot.billed_cost + snapshot.unbilled_estimate
                if total >= self.settings.monthly_limit:
                    state = "exhausted"
                elif total >= self.settings.monthly_limit * self.settings.critical_fraction:
                    state = "critical"
                elif total >= self.settings.monthly_limit * self.settings.warning_fraction:
                    state = "warning"
                else:
                    state = "connected"
        return ApiBudgetView(
            state=state,
            generated_at_utc=generated,
            policy=policy,
            evidence=evidence,
        )


def load_api_budget_reader() -> ApiBudgetReader:
    return ApiBudgetReader(load_api_budget_settings())
