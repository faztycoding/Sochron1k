"""Coherent PA01 policy handoff; never strategy, risk or execution authority."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import threading
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal, Self
from uuid import UUID, uuid4

from pydantic import (
    AwareDatetime,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)

from .execution_bridge import ExecutionPolicySnapshot, ExecutionPollingBridge
from .models import StrictModel
from .telemetry import DemoIdentity, FiniteDecimal, TelemetryBridge

MAX_PRIVATE_BYTES = 16_384
MAX_NEWS_AGE_SECONDS = 300
MAX_SOURCE_AGE_SECONDS = 5
SafeText = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f]+$"),
]


class PolicyWriterSettings(StrictModel):
    identity: DemoIdentity
    archive_id: UUID
    output_file: Path
    news_gate_file: Path

    @field_validator("output_file", "news_gate_file", mode="before")
    @classmethod
    def canonical_path(cls, value: object) -> Path:
        if not isinstance(value, (str, Path)) or not str(value) or "\x00" in str(value):
            raise ValueError("canonical path required")
        path = Path(value)
        if not path.is_absolute() or path.resolve() != path or str(path) != str(value):
            raise ValueError("canonical path required")
        return path

    @model_validator(mode="after")
    def distinct_handoff_paths(self) -> Self:
        if self.output_file == self.news_gate_file:
            raise ValueError("policy output and news input must differ")
        return self


class NewsGateFrame(StrictModel):
    protocol: Literal["sochron.news-gate.v1"]
    source_id: SafeText
    revision: SafeText
    observed_at_utc: AwareDatetime
    coverage_from_utc: AwareDatetime
    coverage_until_utc: AwareDatetime
    complete: Literal[True]
    blocked: StrictBool
    blocking_event_ids: tuple[SafeText, ...] = Field(default=(), max_length=64)

    @field_validator("observed_at_utc", "coverage_from_utc", "coverage_until_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def coherent_coverage(self) -> Self:
        if (
            self.coverage_from_utc >= self.coverage_until_utc
            or not self.coverage_from_utc <= self.observed_at_utc <= self.coverage_until_utc
            or len(set(self.blocking_event_ids)) != len(self.blocking_event_ids)
            or self.blocked != bool(self.blocking_event_ids)
        ):
            raise ValueError("invalid news gate coverage")
        return self


class PolicyObservation(StrictModel):
    evidence_id: SafeText
    observed_at_utc: AwareDatetime

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class PolicyObservations(StrictModel):
    quote: PolicyObservation
    market: PolicyObservation
    news: PolicyObservation
    account: PolicyObservation


class PolicyEvidence(StrictModel):
    cutoff_utc: AwareDatetime
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[^\s]+$")
    feed_id: SafeText
    spread_price: FiniteDecimal = Field(ge=0)
    market_open: StrictBool
    price_stale: Literal[False] = False
    news_blocked: StrictBool
    has_exposure: StrictBool
    has_pending: StrictBool
    ai_enabled: Literal[False] = False
    observations: PolicyObservations

    @field_validator("spread_price", mode="before")
    @classmethod
    def exact_spread(cls, value: object) -> object:
        if not isinstance(value, Decimal):
            raise ValueError("Decimal spread required")
        return value

    @field_validator("cutoff_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

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
            or self.cutoff_utc - self.observations.quote.observed_at_utc
            > timedelta(seconds=MAX_SOURCE_AGE_SECONDS)
        ):
            raise ValueError("invalid policy observations")
        return self


class PolicyWriterStatus(StrictModel):
    state: Literal["disabled", "awaiting_sources", "ready", "degraded"]
    quote_ready: bool = False
    market_ready: bool = False
    account_ready: bool = False
    news_ready: bool = False
    output_fresh: bool = False
    last_written_at_utc: AwareDatetime | None = None
    auto_trading_enabled: Literal[False] = False
    execution_ready: Literal[False] = False


class _AwaitingSource(RuntimeError):
    pass


class _InvalidSource(RuntimeError):
    pass


class _MissingPrivateFile(FileNotFoundError):
    pass


def _file_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _directory_identity(path: Path) -> tuple[int, int]:
    try:
        if not path.is_absolute() or path.resolve() != path:
            raise _InvalidSource()
        info = path.lstat()
        if (
            not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077
        ):
            raise _InvalidSource()
        return info.st_dev, info.st_ino
    except OSError, ValueError, TypeError:
        raise _InvalidSource() from None


def _private_bytes(path: Path, limit: int) -> bytes:
    parent = _directory_identity(path.parent)
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        raise _MissingPrivateFile() from None
    except OSError:
        raise _InvalidSource() from None
    try:
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) & 0o077
                or before.st_size > limit
            ):
                raise _InvalidSource()
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        current = path.lstat()
        if (
            len(data) > limit
            or _file_identity(before) != _file_identity(after)
            or _file_identity(after) != _file_identity(current)
            or _directory_identity(path.parent) != parent
        ):
            raise _InvalidSource()
        return data
    except OSError, ValueError, TypeError:
        raise _InvalidSource() from None


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


def load_policy_writer_settings() -> PolicyWriterSettings | None:
    configured = os.environ.get("SOCHRON_POLICY_WRITER_CONFIG_FILE")
    if not configured:
        return None
    try:
        config_path = Path(configured)
        if (
            not config_path.is_absolute()
            or config_path.resolve() != config_path
            or str(config_path) != configured
        ):
            raise _InvalidSource()
        data = _json(_private_bytes(config_path, MAX_PRIVATE_BYTES))
        if set(data) == {"enabled"} and data["enabled"] is False:
            return None
        expected = set(PolicyWriterSettings.model_fields) | {"enabled"}
        if set(data) != expected or data.pop("enabled", None) is not True:
            raise _InvalidSource()
        settings = PolicyWriterSettings.model_validate(data)
        if config_path in {settings.output_file, settings.news_gate_file}:
            raise _InvalidSource()
        _directory_identity(settings.output_file.parent)
        _directory_identity(settings.news_gate_file.parent)
        return settings
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        _InvalidSource,
        _MissingPrivateFile,
    ):
        raise RuntimeError(
            "Invalid private policy writer configuration; writer not started"
        ) from None


def _canonical(value: StrictModel) -> bytes:
    return json.dumps(
        value.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _evidence_id(kind: str, value: StrictModel) -> str:
    return f"{kind}:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _validate_existing_output(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_nlink != 1
        or stat.S_IMODE(info.st_mode) & 0o077
    ):
        raise _InvalidSource()


def _publish_atomic(path: Path, raw: bytes, parent_identity: tuple[int, int]) -> None:
    if len(raw) > MAX_PRIVATE_BYTES or _directory_identity(path.parent) != parent_identity:
        raise _InvalidSource()
    _validate_existing_output(path)
    temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    created_identity: tuple[int, int] | None = None
    replaced = False
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        with os.fdopen(descriptor, "wb") as stream:
            created = os.fstat(stream.fileno())
            created_identity = created.st_dev, created.st_ino
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
            final = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(final.st_mode)
                or final.st_uid != os.getuid()
                or final.st_nlink != 1
                or stat.S_IMODE(final.st_mode) & 0o077
                or final.st_size != len(raw)
                or (final.st_dev, final.st_ino) != created_identity
            ):
                raise _InvalidSource()
        if _directory_identity(path.parent) != parent_identity:
            raise _InvalidSource()
        _validate_existing_output(path)
        os.replace(temporary, path)
        replaced = True
        _validate_existing_output(path)
        if path.stat().st_size != len(raw):
            raise _InvalidSource()
        directory = os.open(path.parent, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if not replaced and created_identity is not None:
            with suppress(OSError):
                info = temporary.lstat()
                if (info.st_dev, info.st_ino) == created_identity:
                    temporary.unlink()


class PolicyEvidenceWriter:
    def __init__(
        self,
        settings: PolicyWriterSettings | None,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.settings = settings
        self._utc_now = utc_now
        self._lock = threading.Lock()
        self._state: Literal["disabled", "awaiting_sources", "ready", "degraded"] = (
            "disabled" if settings is None else "awaiting_sources"
        )
        self._ready = {"quote": False, "market": False, "account": False, "news": False}
        self._last_written_at: datetime | None = None
        self._output_parent_identity: tuple[int, int] | None = None
        if settings is not None:
            try:
                self._output_parent_identity = _directory_identity(settings.output_file.parent)
                _directory_identity(settings.news_gate_file.parent)
                _validate_existing_output(settings.output_file)
            except _InvalidSource:
                raise RuntimeError(
                    "Invalid private policy writer configuration; writer not started"
                ) from None

    def _now(self) -> datetime:
        value = self._utc_now()
        if value.tzinfo is None or value.utcoffset() is None:
            raise _InvalidSource()
        return value.astimezone(UTC)

    def _news(self, cutoff: datetime) -> NewsGateFrame:
        settings = self.settings
        try:
            frame = NewsGateFrame.model_validate(
                _json(_private_bytes(settings.news_gate_file, MAX_PRIVATE_BYTES))
            )
        except _MissingPrivateFile:
            raise _AwaitingSource() from None
        except ValueError, TypeError, RecursionError, _InvalidSource:
            raise _InvalidSource() from None
        age = (cutoff - frame.observed_at_utc).total_seconds()
        if (
            age < 0
            or age > MAX_NEWS_AGE_SECONDS
            or not frame.coverage_from_utc <= cutoff < frame.coverage_until_utc
        ):
            raise _AwaitingSource()
        return frame

    @staticmethod
    def _account_values(snapshot: ExecutionPolicySnapshot) -> tuple[bool, bool]:
        open_volumes = tuple(
            item.open_position_volume for item in snapshot.frame.inventory.snapshots
        )
        if any(value < 0 for value in open_volumes):
            raise _InvalidSource()
        has_exposure = any(value > 0 for value in open_volumes)
        has_pending = snapshot.active_command or any(
            item.remaining_volume > 0 for item in snapshot.frame.inventory.snapshots
        )
        has_pending = has_pending or any(
            item.remaining_volume > 0 for item in snapshot.frame.inventory.management_snapshots
        )
        return has_exposure, has_pending

    def _build(
        self,
        cutoff: datetime,
        telemetry: TelemetryBridge,
        execution: ExecutionPollingBridge,
    ) -> PolicyEvidence:
        view = telemetry.view()
        observation = view.observation
        if (
            observation is None
            or view.status.state != "connected"
            or not view.status.heartbeat_fresh
            or not view.status.price_fresh
        ):
            raise _AwaitingSource()
        frame = observation.frame
        if frame.identity != self.settings.identity:
            raise _InvalidSource()
        quote_age = (cutoff - observation.event_time_utc).total_seconds()
        if quote_age < 0 or quote_age > MAX_SOURCE_AGE_SECONDS:
            raise _AwaitingSource()
        self._ready["quote"] = True
        if (
            frame.protocol != "sochron.telemetry.v2"
            or frame.market_open is None
            or frame.market_source != "mt5-symbol-trade-session"
        ):
            raise _AwaitingSource()
        self._ready["market"] = True

        try:
            account = execution.policy_snapshot()
        except ConnectionError:
            raise _AwaitingSource() from None
        if account.frame.identity != self.settings.identity:
            raise _InvalidSource()
        account_age = (cutoff - account.frame.observed_at).total_seconds()
        if account_age < 0 or account_age > MAX_SOURCE_AGE_SECONDS:
            raise _AwaitingSource()
        has_exposure, has_pending = self._account_values(account)
        self._ready["account"] = True

        news = self._news(cutoff)
        self._ready["news"] = True
        return PolicyEvidence(
            cutoff_utc=cutoff,
            symbol=self.settings.identity.symbol,
            feed_id=f"mt5-copyrates:{self.settings.archive_id}",
            spread_price=frame.ask - frame.bid,
            market_open=frame.market_open,
            news_blocked=news.blocked,
            has_exposure=has_exposure,
            has_pending=has_pending,
            observations=PolicyObservations(
                quote=PolicyObservation(
                    evidence_id=_evidence_id("quote", frame),
                    observed_at_utc=observation.event_time_utc,
                ),
                market=PolicyObservation(
                    evidence_id=_evidence_id("market", frame),
                    observed_at_utc=observation.event_time_utc,
                ),
                news=PolicyObservation(
                    evidence_id=_evidence_id("news", news),
                    observed_at_utc=news.observed_at_utc,
                ),
                account=PolicyObservation(
                    evidence_id=_evidence_id("account", account),
                    observed_at_utc=account.frame.observed_at,
                ),
            ),
        )

    def refresh(
        self,
        telemetry: TelemetryBridge,
        execution: ExecutionPollingBridge,
    ) -> bool:
        if self.settings is None:
            return False
        with self._lock:
            self._ready = {"quote": False, "market": False, "account": False, "news": False}
            try:
                cutoff = self._now()
                evidence = self._build(cutoff, telemetry, execution)
                _publish_atomic(
                    self.settings.output_file,
                    _canonical(evidence),
                    self._output_parent_identity,
                )
                self._last_written_at = cutoff
                self._state = "ready"
                return True
            except _AwaitingSource:
                self._state = "awaiting_sources"
            except Exception:
                self._state = "degraded"
            return False

    def status(self) -> PolicyWriterStatus:
        with self._lock:
            state = self._state
            fresh = False
            if self._last_written_at is not None:
                try:
                    age = (self._now() - self._last_written_at).total_seconds()
                    fresh = 0 <= age <= MAX_SOURCE_AGE_SECONDS
                except _InvalidSource:
                    state = "degraded"
            if state == "ready" and not fresh:
                state = "awaiting_sources"
            return PolicyWriterStatus(
                state=state,
                quote_ready=self._ready["quote"],
                market_ready=self._ready["market"],
                account_ready=self._ready["account"],
                news_ready=self._ready["news"],
                output_fresh=fresh,
                last_written_at_utc=self._last_written_at,
            )
