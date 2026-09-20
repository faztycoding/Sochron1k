from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError
from sochron_worker.pa01 import PA01Context, evaluate_pa01
from sochron_worker.pa01_aggregation import (
    AGGREGATION_VERSION,
    AggregationUnavailable,
    NativeM1Evidence,
    aggregate_native_m1,
)

D = Decimal
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
SERVER_BASE = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp())
ARCHIVE_ID = UUID("11111111-2222-4333-8444-555555555555")
VALID_FROM = SERVER_BASE - 3_600
VALID_UNTIL = SERVER_BASE + 6_120 * 60 + 3_600


def native_m1(
    index: int,
    *,
    offset: int = 7_200,
    archive_id: UUID = ARCHIVE_ID,
    available_delay: int = 2,
) -> NativeM1Evidence:
    time_server_s = SERVER_BASE + index * 60
    opened = EPOCH + timedelta(seconds=time_server_s - offset)
    confirmed = time_server_s + 60
    confirmed_at = EPOCH + timedelta(seconds=confirmed - offset)
    price = D("2500.00") + D(index) / D("100")
    return NativeM1Evidence(
        archive_id=archive_id,
        symbol="XAUUSD.fixture",
        time_server_s=time_server_s,
        broker_utc_offset_seconds=offset,
        offset_valid_from_server_s=VALID_FROM,
        offset_valid_until_server_s=VALID_UNTIL,
        open_time_utc=opened,
        confirmed_by_server_s=confirmed,
        source_observed_at_utc=confirmed_at,
        first_received_at_utc=confirmed_at + timedelta(seconds=1),
        available_at_utc=confirmed_at + timedelta(seconds=available_delay),
        first_receipt=index + 1,
        terminal_build=5_550,
        open=price,
        high=price + D("0.05"),
        low=price - D("0.05"),
        close=price + D("0.01"),
        tick_volume=100 + index,
        spread_points=12,
        tick_size=D("0.01"),
        digits=2,
    )


def cutoff(rows: tuple[NativeM1Evidence, ...]) -> datetime:
    return max(row.available_at_utc for row in rows)


def context(result) -> PA01Context:
    return PA01Context(
        cutoff_utc=result.cutoff_utc,
        symbol=result.symbol,
        feed_id=result.feed_id,
        spread_price=D("0.01"),
        market_open=True,
        price_stale=False,
        news_blocked=False,
        has_exposure=False,
        has_pending=False,
    )


def test_exact_complete_m5_h1_buckets_and_provenance_are_deterministic():
    rows = tuple(native_m1(index) for index in range(60))
    result = aggregate_native_m1(rows, cutoff_utc=cutoff(rows))
    repeated = aggregate_native_m1(rows, cutoff_utc=cutoff(rows))

    assert result == repeated
    assert result.aggregation_version == AGGREGATION_VERSION
    assert result.as_of_source_row_count == 60
    assert len(result.m5_bars) == 12
    assert len(result.h1_bars) == 1
    first_m5 = result.m5_bars[0]
    assert first_m5.open == rows[0].open
    assert first_m5.high == max(row.high for row in rows[:5])
    assert first_m5.low == min(row.low for row in rows[:5])
    assert first_m5.close == rows[4].close
    assert first_m5.available_at_utc == rows[4].available_at_utc
    assert first_m5.time_server_s == SERVER_BASE
    assert first_m5.evidence_id == f"native-m5:{ARCHIVE_ID}:{SERVER_BASE}"
    assert first_m5.source_revision.startswith(f"{AGGREGATION_VERSION}:")
    h1 = result.h1_bars[0]
    assert h1.open == rows[0].open
    assert h1.close == rows[-1].close
    assert h1.available_at_utc == rows[-1].available_at_utc
    assert result.order_created is False
    assert result.risk_admitted is False


def test_non_whole_hour_offset_keeps_broker_h1_boundary_and_exact_utc():
    rows = tuple(native_m1(index, offset=19_800) for index in range(60))
    result = aggregate_native_m1(rows, cutoff_utc=cutoff(rows))
    h1 = result.h1_bars[0]
    assert h1.time_server_s % 3_600 == 0
    assert h1.broker_utc_offset_seconds == 19_800
    assert h1.open_time_utc == EPOCH + timedelta(seconds=SERVER_BASE - 19_800)
    assert h1.open_time_utc.minute == 30


def test_partial_and_gapped_buckets_are_omitted_without_fabrication():
    complete = tuple(native_m1(index) for index in range(60))
    rows = complete[:12] + complete[13:]
    result = aggregate_native_m1(rows, cutoff_utc=cutoff(rows))
    assert len(result.m5_bars) == 11
    assert not result.h1_bars
    assert all(bar.time_server_s != SERVER_BASE + 10 * 60 for bar in result.m5_bars)
    assert all(bar.gap_reason_before == "none" for bar in result.m5_bars)


def test_cutoff_excludes_later_availability_and_future_append_is_inert():
    rows = tuple(native_m1(index) for index in range(65))
    early_cutoff = rows[54].available_at_utc
    expected = aggregate_native_m1(rows[:55], cutoff_utc=early_cutoff)
    observed = aggregate_native_m1(rows, cutoff_utc=early_cutoff)
    assert observed == expected
    assert observed.as_of_source_row_count == 55
    assert len(observed.m5_bars) == 11
    assert not observed.h1_bars

    delayed = list(rows[:60])
    delayed[24] = delayed[24].model_copy(
        update={"available_at_utc": delayed[24].available_at_utc + timedelta(days=1)}
    )
    delayed_result = aggregate_native_m1(
        tuple(delayed), cutoff_utc=max(row.available_at_utc for row in rows[:60])
    )
    assert delayed_result.as_of_source_row_count == 59
    assert len(delayed_result.m5_bars) == 11
    assert not delayed_result.h1_bars


@pytest.mark.parametrize(
    "mutate",
    [
        lambda row: row.model_copy(update={"archive_id": UUID(int=2)}),
        lambda row: row.model_copy(update={"symbol": "OTHER"}),
        lambda row: row.model_copy(update={"broker_utc_offset_seconds": 10_800}),
        lambda row: row.model_copy(update={"tick_size": D("0.10")}),
    ],
)
def test_mixed_binding_or_revision_fails_closed(mutate):
    rows = [native_m1(index) for index in range(5)]
    rows[-1] = mutate(rows[-1])
    with pytest.raises(AggregationUnavailable, match="PA01_AGGREGATION_UNAVAILABLE"):
        aggregate_native_m1(tuple(rows), cutoff_utc=cutoff(tuple(rows)))


def test_duplicate_server_time_fails_and_changed_child_changes_revision_hash():
    rows = tuple(native_m1(index) for index in range(5))
    duplicate = rows[-1].model_copy(update={"close": rows[-1].close - D("0.01")})
    with pytest.raises(AggregationUnavailable):
        aggregate_native_m1((*rows, duplicate), cutoff_utc=cutoff(rows))
    forged = tuple(
        row.model_copy(update={"open_time_utc": row.open_time_utc + timedelta(seconds=1)})
        for row in rows
    )
    with pytest.raises(AggregationUnavailable):
        aggregate_native_m1(forged, cutoff_utc=cutoff(rows))

    changed = list(rows)
    changed[2] = changed[2].model_copy(update={"close": changed[2].close + D("0.01")})
    original = aggregate_native_m1(rows, cutoff_utc=cutoff(rows))
    revised = aggregate_native_m1(tuple(changed), cutoff_utc=cutoff(tuple(changed)))
    assert revised.m5_bars[0].evidence_id == original.m5_bars[0].evidence_id
    assert revised.m5_bars[0].source_revision != original.m5_bars[0].source_revision
    assert revised.source_dataset_hash != original.source_dataset_hash
    assert revised.aggregation_hash != original.aggregation_hash


def test_bounded_output_is_accepted_directly_by_pa01_and_gap_blocks():
    rows = tuple(native_m1(index) for index in range(720))
    result = aggregate_native_m1(rows, cutoff_utc=cutoff(rows))
    assert len(result.m5_bars) == 100
    assert len(result.h1_bars) == 12
    decision = evaluate_pa01(
        context(result), m5_bars=result.m5_bars, h1_bars=result.h1_bars
    )
    assert decision.action == "wait"
    assert decision.reason_code == "STRUCTURE_INCOMPLETE"

    gapped = rows[:512] + rows[513:]
    gapped_result = aggregate_native_m1(gapped, cutoff_utc=cutoff(gapped))
    blocked = evaluate_pa01(
        context(gapped_result),
        m5_bars=gapped_result.m5_bars,
        h1_bars=gapped_result.h1_bars,
    )
    assert (blocked.action, blocked.reason_code) == ("block", "DATA_GAP")


@pytest.mark.parametrize(
    "change",
    [
        {"open": "2500.00"},
        {"price_basis": "last"},
        {"open_time_utc": datetime(2026, 1, 1)},
        {"time_server_s": SERVER_BASE + 1},
        {"broker_utc_offset_seconds": 1},
        {"offset_valid_until_server_s": SERVER_BASE + 60},
        {"open": D("2500.001")},
        {
            "source_observed_at_utc": EPOCH
            + timedelta(seconds=SERVER_BASE + 60 - 7_200 - 1)
        },
    ],
)
def test_malformed_native_source_evidence_is_rejected(change):
    values = native_m1(0).model_dump()
    values.update(change)
    with pytest.raises(ValidationError):
        NativeM1Evidence(**values)


def test_aggregation_is_a_pure_non_authoritative_boundary():
    source = Path("services/worker/src/sochron_worker/pa01_aggregation.py").read_text()
    for forbidden in (
        "import httpx",
        "import requests",
        "import os",
        "datetime.now",
        "supabase",
        "sqlite3",
        "OrderSend",
        "ExecutionService",
        "service_role",
        "open(",
    ):
        assert forbidden not in source
    assert "order_created: Literal[False]" in source
    assert "risk_admitted: Literal[False]" in source
