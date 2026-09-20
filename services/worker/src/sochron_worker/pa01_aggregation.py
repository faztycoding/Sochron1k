"""Pure native M1 to PA01 M5/H1 aggregation; no I/O or execution authority."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, StrictInt, field_validator, model_validator
from sochron1k.models import StrictModel
from sochron1k.telemetry import FiniteDecimal

from .pa01 import H1_SECONDS, M5_SECONDS, MAX_WINDOW, ClosedBar

AGGREGATION_VERSION = "native-pa01-aggregation-v1"
SOURCE_REVISION = "native-v1"
M1_SECONDS = 60
MAX_SOURCE_ROWS = 6_120
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class AggregationUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("PA01_AGGREGATION_UNAVAILABLE")


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class NativeM1Evidence(StrictModel):
    """One synchronized immutable native-v1 M1 row plus its availability envelope."""

    archive_id: UUID
    source_revision: Literal["native-v1"] = SOURCE_REVISION
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[^\s]+$")
    price_basis: Literal["bid"] = "bid"
    closed: Literal[True] = True
    time_server_s: StrictInt = Field(gt=0, le=4_102_444_800)
    broker_utc_offset_seconds: StrictInt = Field(ge=-50_400, le=50_400)
    offset_valid_from_server_s: StrictInt = Field(gt=0, le=4_102_444_800)
    offset_valid_until_server_s: StrictInt = Field(gt=0, le=4_102_444_800)
    open_time_utc: AwareDatetime
    confirmed_by_server_s: StrictInt = Field(gt=0, le=4_102_444_800)
    source_observed_at_utc: AwareDatetime
    first_received_at_utc: AwareDatetime
    available_at_utc: AwareDatetime
    first_receipt: StrictInt = Field(ge=1, le=9_007_199_254_740_991)
    terminal_build: StrictInt = Field(gt=0, le=9_007_199_254_740_991)
    open: FiniteDecimal = Field(gt=0)
    high: FiniteDecimal = Field(gt=0)
    low: FiniteDecimal = Field(gt=0)
    close: FiniteDecimal = Field(gt=0)
    tick_volume: StrictInt = Field(ge=1, le=9_007_199_254_740_991)
    spread_points: StrictInt = Field(ge=0, le=2_147_483_647)
    tick_size: FiniteDecimal = Field(gt=0)
    digits: StrictInt = Field(ge=0, le=10)

    @field_validator("open", "high", "low", "close", "tick_size", mode="before")
    @classmethod
    def exact_decimals(cls, value: object) -> object:
        if not isinstance(value, Decimal):
            raise ValueError("Decimal evidence required")
        return value

    @field_validator(
        "open_time_utc",
        "source_observed_at_utc",
        "first_received_at_utc",
        "available_at_utc",
    )
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def exact_native_m1(self) -> Self:
        expected_open = EPOCH + timedelta(
            seconds=self.time_server_s - self.broker_utc_offset_seconds
        )
        confirmed_at = EPOCH + timedelta(
            seconds=self.confirmed_by_server_s - self.broker_utc_offset_seconds
        )
        if (
            self.time_server_s % M1_SECONDS
            or self.confirmed_by_server_s % M1_SECONDS
            or self.broker_utc_offset_seconds % M1_SECONDS
            or self.confirmed_by_server_s <= self.time_server_s
            or not self.offset_valid_from_server_s
            <= self.time_server_s
            < self.confirmed_by_server_s
            < self.offset_valid_until_server_s
            or self.open_time_utc != expected_open
            or self.source_observed_at_utc < confirmed_at
            or self.first_received_at_utc < self.source_observed_at_utc
            or self.available_at_utc < self.first_received_at_utc
        ):
            raise ValueError("invalid native M1 timing")
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("invalid OHLC range")
        tick_num, tick_den = self.tick_size.as_integer_ratio()
        for price in (self.open, self.high, self.low, self.close):
            num, den = price.as_integer_ratio()
            if num * tick_den % (den * tick_num) or num * 10**self.digits % den:
                raise ValueError("price is outside the admitted grid")
        return self

    @property
    def close_time_utc(self) -> datetime:
        return self.open_time_utc + timedelta(seconds=M1_SECONDS)

    @property
    def evidence_id(self) -> str:
        return f"native-m1:{self.archive_id}:{self.time_server_s}"


class PA01Aggregation(StrictModel):
    aggregation_version: Literal["native-pa01-aggregation-v1"] = AGGREGATION_VERSION
    cutoff_utc: AwareDatetime
    archive_id: UUID
    feed_id: str = Field(min_length=1, max_length=128)
    source_revision: Literal["native-v1"] = SOURCE_REVISION
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[^\s]+$")
    price_basis: Literal["bid"] = "bid"
    broker_utc_offset_seconds: StrictInt = Field(ge=-50_400, le=50_400)
    offset_valid_from_server_s: StrictInt = Field(gt=0, le=4_102_444_800)
    offset_valid_until_server_s: StrictInt = Field(gt=0, le=4_102_444_800)
    as_of_source_row_count: StrictInt = Field(ge=0, le=MAX_SOURCE_ROWS)
    first_time_server_s: StrictInt | None = Field(default=None, gt=0)
    last_time_server_s: StrictInt | None = Field(default=None, gt=0)
    source_dataset_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    aggregation_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    m5_bars: tuple[ClosedBar, ...] = Field(max_length=MAX_WINDOW)
    h1_bars: tuple[ClosedBar, ...] = Field(max_length=MAX_WINDOW)
    order_created: Literal[False] = False
    risk_admitted: Literal[False] = False

    @field_validator("cutoff_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def exact_projection(self) -> Self:
        if (
            self.feed_id != f"mt5-copyrates:{self.archive_id}"
            or self.offset_valid_from_server_s >= self.offset_valid_until_server_s
            or (self.as_of_source_row_count == 0)
            != (self.first_time_server_s is None and self.last_time_server_s is None)
            or (self.first_time_server_s is None) != (self.last_time_server_s is None)
            or (
                self.first_time_server_s is not None
                and self.last_time_server_s is not None
                and self.first_time_server_s > self.last_time_server_s
            )
        ):
            raise ValueError("invalid aggregation projection")
        for timeframe, bars in (("M5", self.m5_bars), ("H1", self.h1_bars)):
            times = [bar.time_server_s for bar in bars]
            if times != sorted(set(times)) or any(
                bar.timeframe != timeframe
                or bar.feed_id != self.feed_id
                or bar.symbol != self.symbol
                or bar.broker_utc_offset_seconds != self.broker_utc_offset_seconds
                or bar.gap_reason_before != "none"
                or not bar.source_revision.startswith(f"{AGGREGATION_VERSION}:")
                for bar in bars
            ):
                raise ValueError("invalid aggregate bars")
        return self


def _canonical_m1(bar: NativeM1Evidence) -> dict[str, object]:
    return {
        "archive_id": str(bar.archive_id),
        "source_revision": bar.source_revision,
        "symbol": bar.symbol,
        "price_basis": bar.price_basis,
        "closed": bar.closed,
        "time_server_s": bar.time_server_s,
        "broker_utc_offset_seconds": bar.broker_utc_offset_seconds,
        "offset_valid_from_server_s": bar.offset_valid_from_server_s,
        "offset_valid_until_server_s": bar.offset_valid_until_server_s,
        "open_time_utc": bar.open_time_utc.isoformat(),
        "confirmed_by_server_s": bar.confirmed_by_server_s,
        "source_observed_at_utc": bar.source_observed_at_utc.isoformat(),
        "first_received_at_utc": bar.first_received_at_utc.isoformat(),
        "available_at_utc": bar.available_at_utc.isoformat(),
        "first_receipt": bar.first_receipt,
        "terminal_build": bar.terminal_build,
        "open": _decimal_text(bar.open),
        "high": _decimal_text(bar.high),
        "low": _decimal_text(bar.low),
        "close": _decimal_text(bar.close),
        "tick_volume": bar.tick_volume,
        "spread_points": bar.spread_points,
        "tick_size": _decimal_text(bar.tick_size),
        "digits": bar.digits,
    }


def _aggregate_buckets(
    rows: tuple[NativeM1Evidence, ...],
    *,
    timeframe: Literal["M5", "H1"],
    period: int,
    feed_id: str,
) -> tuple[ClosedBar, ...]:
    grouped: dict[int, list[NativeM1Evidence]] = defaultdict(list)
    for row in rows:
        grouped[row.time_server_s // period * period].append(row)

    result: list[ClosedBar] = []
    count = period // M1_SECONDS
    for bucket_start in sorted(grouped):
        children = sorted(grouped[bucket_start], key=lambda row: row.time_server_s)
        expected = tuple(range(bucket_start, bucket_start + period, M1_SECONDS))
        if len(children) != count or tuple(row.time_server_s for row in children) != expected:
            continue
        revision = _digest([_canonical_m1(row) for row in children])
        first, last = children[0], children[-1]
        result.append(
            ClosedBar(
                evidence_id=(
                    f"native-{timeframe.lower()}:{first.archive_id}:{bucket_start}"
                ),
                feed_id=feed_id,
                source_revision=f"{AGGREGATION_VERSION}:{revision}",
                symbol=first.symbol,
                price_basis="bid",
                timeframe=timeframe,
                time_server_s=bucket_start,
                broker_utc_offset_seconds=first.broker_utc_offset_seconds,
                open_time_utc=EPOCH
                + timedelta(seconds=bucket_start - first.broker_utc_offset_seconds),
                available_at_utc=max(row.available_at_utc for row in children),
                open=first.open,
                high=max(row.high for row in children),
                low=min(row.low for row in children),
                close=last.close,
                tick_size=first.tick_size,
                digits=first.digits,
                gap_reason_before="none",
            )
        )
    return tuple(result[-MAX_WINDOW:])


def aggregate_native_m1(
    rows: tuple[NativeM1Evidence, ...], *, cutoff_utc: datetime
) -> PA01Aggregation:
    """Return bounded complete M5/H1 evidence at an explicit cutoff."""
    try:
        if (
            not isinstance(rows, tuple)
            or not 1 <= len(rows) <= MAX_SOURCE_ROWS
            or not isinstance(cutoff_utc, datetime)
            or cutoff_utc.tzinfo is None
            or cutoff_utc.utcoffset() is None
            or any(not isinstance(row, NativeM1Evidence) for row in rows)
        ):
            raise AggregationUnavailable()
        cutoff = cutoff_utc.astimezone(UTC)
        checked = tuple(NativeM1Evidence.model_validate(row.model_dump()) for row in rows)
        first = checked[0]
        binding = (
            first.archive_id,
            first.source_revision,
            first.symbol,
            first.price_basis,
            first.broker_utc_offset_seconds,
            first.offset_valid_from_server_s,
            first.offset_valid_until_server_s,
            first.tick_size,
            first.digits,
        )
        if any(
            (
                row.archive_id,
                row.source_revision,
                row.symbol,
                row.price_basis,
                row.broker_utc_offset_seconds,
                row.offset_valid_from_server_s,
                row.offset_valid_until_server_s,
                row.tick_size,
                row.digits,
            )
            != binding
            for row in checked
        ):
            raise AggregationUnavailable()
        if len({row.time_server_s for row in checked}) != len(checked):
            raise AggregationUnavailable()

        eligible = tuple(
            sorted(
                (
                    row
                    for row in checked
                    if row.close_time_utc <= cutoff and row.available_at_utc <= cutoff
                ),
                key=lambda row: row.time_server_s,
            )
        )
        feed_id = f"mt5-copyrates:{first.archive_id}"
        source_hash = _digest([_canonical_m1(row) for row in eligible])
        m5 = _aggregate_buckets(
            eligible, timeframe="M5", period=M5_SECONDS, feed_id=feed_id
        )
        h1 = _aggregate_buckets(
            eligible, timeframe="H1", period=H1_SECONDS, feed_id=feed_id
        )
        output_hash = _digest(
            {
                "aggregation_version": AGGREGATION_VERSION,
                "cutoff_utc": cutoff.isoformat(),
                "source_dataset_hash": source_hash,
                "m5": [bar.model_dump(mode="json") for bar in m5],
                "h1": [bar.model_dump(mode="json") for bar in h1],
            }
        )
        return PA01Aggregation(
            cutoff_utc=cutoff,
            archive_id=first.archive_id,
            feed_id=feed_id,
            symbol=first.symbol,
            broker_utc_offset_seconds=first.broker_utc_offset_seconds,
            offset_valid_from_server_s=first.offset_valid_from_server_s,
            offset_valid_until_server_s=first.offset_valid_until_server_s,
            as_of_source_row_count=len(eligible),
            first_time_server_s=eligible[0].time_server_s if eligible else None,
            last_time_server_s=eligible[-1].time_server_s if eligible else None,
            source_dataset_hash=source_hash,
            aggregation_hash=output_hash,
            m5_bars=m5,
            h1_bars=h1,
        )
    except AggregationUnavailable:
        raise
    except (ValueError, TypeError, ArithmeticError, OverflowError, RecursionError):
        raise AggregationUnavailable() from None
