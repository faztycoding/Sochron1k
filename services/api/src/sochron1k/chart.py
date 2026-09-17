"""Bounded native-bar monitoring cache; not research history or execution truth."""

from __future__ import annotations

import hashlib
import os
import stat
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictInt, field_validator, model_validator

from .models import StrictModel
from .telemetry import (
    BridgeDenied,
    BridgeStatus,
    DemoIdentity,
    FiniteDecimal,
    FrameReceipt,
    TelemetryBridge,
)

if TYPE_CHECKING:
    from .bar_history import BarHistory

MAX_CHART_BYTES = 131_072
MAX_CHART_AGE_SECONDS = 15
PERIODS = {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}
Timeframe = Literal["M1", "M5", "M15", "H1"]
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class ChartSettings(StrictModel):
    offset_valid_from_server_s: StrictInt = Field(gt=0, le=4_102_444_800)
    offset_valid_until_server_s: StrictInt = Field(gt=0, le=4_102_444_800)

    @model_validator(mode="after")
    def ordered_interval(self) -> Self:
        if self.offset_valid_from_server_s >= self.offset_valid_until_server_s:
            raise ValueError("invalid offset validity interval")
        return self


def load_chart_settings() -> ChartSettings | None:
    configured = os.environ.get("SOCHRON_CHART_CONFIG_FILE")
    if not configured:
        return None
    try:
        with os.fdopen(
            os.open(Path(configured), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb"
        ) as stream:
            metadata = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.getuid()
                or stat.S_IMODE(metadata.st_mode) & 0o077
            ):
                raise ValueError("private configuration required")
            raw = stream.read(16_385)
        if len(raw) > 16_384:
            raise ValueError("configuration too large")
        return ChartSettings.model_validate_json(raw)
    except OSError, ValueError:
        raise RuntimeError(
            "Invalid private chart configuration; chart ingress not started"
        ) from None


class NativeBar(StrictModel):
    time_server_s: StrictInt = Field(gt=0, le=4_102_444_800)
    open: FiniteDecimal = Field(gt=0)
    high: FiniteDecimal = Field(gt=0)
    low: FiniteDecimal = Field(gt=0)
    close: FiniteDecimal = Field(gt=0)
    tick_volume: StrictInt = Field(ge=1, le=9_007_199_254_740_991)
    spread_points: StrictInt = Field(ge=0, le=2_147_483_647)

    @model_validator(mode="after")
    def price_range(self) -> Self:
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("invalid OHLC range")
        return self


class ChartFrame(StrictModel):
    protocol: Literal["sochron.chart.v1"]
    source: Literal["mt5-copyrates"]
    boot_id: UUID
    sequence: StrictInt = Field(ge=1, le=9_007_199_254_740_991)
    identity: DemoIdentity
    trade_mode: Literal["demo"]
    terminal_build: StrictInt = Field(gt=0)
    observed_at: AwareDatetime
    broker_utc_offset_seconds: StrictInt = Field(ge=-50_400, le=50_400)
    timeframe: Timeframe
    price_basis: Literal["bid", "last"]
    digits: StrictInt = Field(ge=0, le=10)
    tick_size: FiniteDecimal = Field(gt=0)
    bars: tuple[NativeBar, ...] = Field(min_length=2, max_length=240)

    @field_validator("observed_at")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def bar_order_and_grid(self) -> Self:
        period = PERIODS[self.timeframe]
        previous = 0
        for bar in self.bars:
            if bar.time_server_s <= previous or bar.time_server_s % period:
                raise ValueError("invalid bar order or period alignment")
            previous = bar.time_server_s
            for price in (bar.open, bar.high, bar.low, bar.close):
                # Decimal arithmetic must be exact even at the admitted 24-digit bound.
                if (
                    price.as_integer_ratio()[0]
                    * self.tick_size.as_integer_ratio()[1]
                    % (price.as_integer_ratio()[1] * self.tick_size.as_integer_ratio()[0])
                ):
                    raise ValueError("price outside tick grid")
                numerator, denominator = price.as_integer_ratio()
                if numerator * 10**self.digits % denominator:
                    raise ValueError("price exceeds symbol digits")
        return self


class ChartBar(NativeBar):
    open_time_utc: datetime
    closed: bool


class ChartGap(StrictModel):
    after_open_time_utc: datetime
    before_open_time_utc: datetime
    missing_intervals: int
    classification: Literal["unclassified"] = "unclassified"


class ChartObservation(StrictModel):
    source: Literal["mt5-copyrates"] = "mt5-copyrates"
    identity: DemoIdentity
    timeframe: Timeframe
    price_basis: Literal["bid", "last"]
    sequence: int
    terminal_build: int
    digits: int
    tick_size: Decimal
    broker_utc_offset_seconds: int
    observed_at: datetime
    received_time_utc: datetime
    bars: tuple[ChartBar, ...]
    gaps: tuple[ChartGap, ...]


class ChartView(StrictModel):
    state: Literal["disabled", "awaiting_snapshot", "ready", "stale", "rejected"]
    snapshot_age_seconds: float | None = None
    latest_bar_age_seconds: float | None = None
    feed_status: BridgeStatus
    observation: ChartObservation | None = None
    execution_ready: Literal[False] = False


class ChartStore:
    def __init__(
        self,
        bridge: TelemetryBridge,
        settings: ChartSettings | None,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
        monotonic: Callable[[], float] = time.monotonic,
        history: BarHistory | None = None,
    ) -> None:
        self.bridge = bridge
        self.settings = settings
        self._now, self._monotonic = utc_now, monotonic
        self._lock = threading.Lock()
        self.history = history
        self._history_failed = False
        self._sequence = 0
        self._fingerprint: str | None = None
        # Restored frames constrain validation only, never initialize live views.
        self._frames: dict[str, ChartFrame] = history.latest_frames() if history else {}
        self._views: dict[str, ChartObservation] = {}
        self._received_mono: dict[str, float] = {}
        self._rejected: set[str] = set()

    @property
    def enabled(self) -> bool:
        return self.settings is not None and self.bridge.settings is not None

    def next_sequence(self) -> int:
        with self._lock:
            return self._sequence + 1

    def reject(self) -> None:
        with self._lock:
            self._rejected.update(PERIODS)

    def fail_history(self) -> None:
        with self._lock:
            self._history_failed = True
            self._rejected.update(PERIODS)

    def accept(self, frame: ChartFrame) -> FrameReceipt:
        from .bar_history import HistoryUnavailable

        fingerprint = hashlib.sha256(frame.model_dump_json().encode()).hexdigest()
        with self._lock:
            try:
                if self._history_failed:
                    raise HistoryUnavailable()
                return self._accept(frame, fingerprint)
            except HistoryUnavailable:
                self._history_failed = True
                self._rejected.update(PERIODS)
                raise
            except BridgeDenied:
                self._rejected.update(PERIODS)
                raise

    def _accept(self, frame: ChartFrame, fingerprint: str) -> FrameReceipt:
        if not self.enabled:
            raise BridgeDenied("CHART_DISABLED")
        settings, bridge_settings = self.settings, self.bridge.settings
        if frame.boot_id != self.bridge.boot_id:
            raise BridgeDenied("BOOT_MISMATCH")
        if frame.identity != bridge_settings.identity:
            raise BridgeDenied("IDENTITY_MISMATCH")
        if frame.broker_utc_offset_seconds != bridge_settings.broker_utc_offset_seconds:
            raise BridgeDenied("CLOCK_OFFSET_MISMATCH")
        if frame.sequence == self._sequence:
            if fingerprint != self._fingerprint:
                raise BridgeDenied("SEQUENCE_CONFLICT")
            return FrameReceipt(duplicate=True, sequence=frame.sequence)
        if frame.sequence < self._sequence:
            raise BridgeDenied("OUT_OF_ORDER")
        telemetry = self.bridge.view()
        contract = telemetry.observation
        if contract is None or telemetry.status.state == "rejected":
            raise BridgeDenied("CHART_CONTRACT_UNAVAILABLE")
        if (
            frame.terminal_build != contract.frame.terminal_build
            or frame.digits != contract.frame.contract.digits
            or frame.tick_size != contract.frame.contract.tick_size
        ):
            raise BridgeDenied("CHART_CONTRACT_MISMATCH")
        now = self._now()
        if not 0 <= (now - frame.observed_at).total_seconds() <= 5:
            raise BridgeDenied("OBSERVATION_CLOCK_INVALID")
        server_now = (frame.observed_at - EPOCH).total_seconds() + frame.broker_utc_offset_seconds
        if (
            frame.bars[0].time_server_s < settings.offset_valid_from_server_s
            or server_now >= settings.offset_valid_until_server_s
        ):
            raise BridgeDenied("OFFSET_VALIDITY_EXCEEDED")
        if frame.bars[-1].time_server_s > server_now:
            raise BridgeDenied("BAR_FROM_FUTURE")
        previous = self._frames.get(frame.timeframe)
        if previous is not None:
            if (
                frame.observed_at < previous.observed_at
                or frame.bars[-1].time_server_s < previous.bars[-1].time_server_s
                or frame.bars[0].time_server_s < previous.bars[0].time_server_s
            ):
                raise BridgeDenied("TIME_REVERSAL")
            if frame.price_basis != previous.price_basis:
                raise BridgeDenied("PRICE_BASIS_CHANGED")
            old_bars = {bar.time_server_s: bar for bar in previous.bars}
            new_bars = {bar.time_server_s: bar for bar in frame.bars}
            # A rolling window cannot silently omit a previously observed interior bar.
            for timestamp in old_bars:
                if frame.bars[0].time_server_s <= timestamp and timestamp not in new_bars:
                    raise BridgeDenied("BAR_DISAPPEARED")
            for bar in frame.bars:
                old = old_bars.get(bar.time_server_s)
                if old is None:
                    continue
                if old != previous.bars[-1]:
                    if old != bar:
                        raise BridgeDenied("CLOSED_BAR_CHANGED")
                elif (
                    bar.open != old.open
                    or bar.high < old.high
                    or bar.low > old.low
                    or bar.tick_volume < old.tick_volume
                ):
                    raise BridgeDenied("FORMING_BAR_REGRESSED")
        period = PERIODS[frame.timeframe]
        bars = tuple(
            ChartBar(
                **bar.model_dump(),
                open_time_utc=EPOCH
                + timedelta(seconds=bar.time_server_s - frame.broker_utc_offset_seconds),
                closed=index < len(frame.bars) - 1,
            )
            for index, bar in enumerate(frame.bars)
        )
        gaps = tuple(
            ChartGap(
                after_open_time_utc=left.open_time_utc,
                before_open_time_utc=right.open_time_utc,
                missing_intervals=(right.time_server_s - left.time_server_s) // period - 1,
            )
            for left, right in pairwise(bars)
            if right.time_server_s - left.time_server_s > period
        )
        observation = ChartObservation(
            identity=frame.identity,
            timeframe=frame.timeframe,
            price_basis=frame.price_basis,
            sequence=frame.sequence,
            terminal_build=frame.terminal_build,
            digits=frame.digits,
            tick_size=frame.tick_size,
            broker_utc_offset_seconds=frame.broker_utc_offset_seconds,
            observed_at=frame.observed_at,
            received_time_utc=now,
            bars=bars,
            gaps=gaps,
        )
        if self.history is not None:
            self.history.record(frame, observation)
        self._views[frame.timeframe] = observation
        self._frames[frame.timeframe] = frame
        self._received_mono[frame.timeframe] = self._monotonic()
        self._sequence, self._fingerprint = frame.sequence, fingerprint
        self._rejected.discard(frame.timeframe)
        return FrameReceipt(duplicate=False, sequence=frame.sequence)

    def view(self, timeframe: Timeframe) -> ChartView:
        with self._lock:
            telemetry = self.bridge.view()
            feed = telemetry.status
            if not self.enabled:
                return ChartView(state="disabled", feed_status=feed)
            observation = self._views.get(timeframe)
            if observation is not None and telemetry.observation is not None:
                current = telemetry.observation.frame
                if (
                    observation.terminal_build != current.terminal_build
                    or observation.tick_size != current.contract.tick_size
                    or observation.digits != current.contract.digits
                ):
                    self._rejected.add(timeframe)
            if timeframe in self._rejected:
                return ChartView(state="rejected", feed_status=feed, observation=observation)
            if observation is None:
                return ChartView(state="awaiting_snapshot", feed_status=feed)
            now = self._now()
            elapsed = max(0, self._monotonic() - self._received_mono[timeframe])
            age = max(
                (now - observation.observed_at).total_seconds(),
                (observation.received_time_utc - observation.observed_at).total_seconds() + elapsed,
            )
            last_open = observation.bars[-1].open_time_utc
            bar_age = max(
                (now - last_open).total_seconds(),
                (observation.received_time_utc - last_open).total_seconds() + elapsed,
            )
            fresh = (
                now >= observation.received_time_utc
                and age <= MAX_CHART_AGE_SECONDS
                and bar_age < PERIODS[timeframe]
                and feed.state == "connected"
            )
            return ChartView(
                state="ready" if fresh else "stale",
                snapshot_age_seconds=round(age, 3),
                latest_bar_age_seconds=round(bar_age, 3),
                feed_status=feed,
                observation=observation,
            )
