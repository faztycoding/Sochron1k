from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from sochron_worker.pa01 import (
    H1_SECONDS,
    M5_SECONDS,
    PARAMETER_HASH,
    ClosedBar,
    EvidenceUnavailable,
    PA01Context,
    adx,
    atr,
    ema,
    evaluate_pa01,
    pivots,
    wilder,
)

BASE = datetime(2026, 1, 1, tzinfo=UTC)
D = Decimal


def make_bar(
    timeframe: str,
    index: int,
    *,
    close: Decimal,
    high: Decimal | None = None,
    low: Decimal | None = None,
    available_delay: int = 1,
    gap: str = "none",
) -> ClosedBar:
    seconds = M5_SECONDS if timeframe == "M5" else H1_SECONDS
    origin = BASE if timeframe == "M5" else BASE - timedelta(days=2)
    opened = origin + timedelta(seconds=index * seconds)
    high = high if high is not None else close + D("0.40")
    low = low if low is not None else close - D("0.40")
    return ClosedBar(
        evidence_id=f"{timeframe.lower()}-{index}",
        feed_id="fixture-feed",
        source_revision="fixture-v1",
        symbol="XAUUSD.fixture",
        timeframe=timeframe,
        open_time_utc=opened,
        available_at_utc=opened + timedelta(seconds=seconds + available_delay),
        open=close,
        high=high,
        low=low,
        close=close,
        tick_size=D("0.01"),
        digits=2,
        gap_reason_before=gap,
    )


def m5_trend(side: str = "buy") -> tuple[ClosedBar, ...]:
    sign = D("1") if side == "buy" else D("-1")
    anchor = D("100") if side == "buy" else D("200")
    bars = [make_bar("M5", index, close=anchor + sign * D("0.05") * index) for index in range(60)]
    previous_close = anchor + sign * D("0.05") * 58
    if side == "buy":
        bars[58] = make_bar(
            "M5", 58, close=previous_close,
            high=previous_close + D("0.40"), low=previous_close - D("0.60"),
        )
        bars[59] = make_bar(
            "M5", 59, close=previous_close + D("0.50"),
            high=previous_close + D("0.60"), low=previous_close - D("0.20"),
        )
    else:
        bars[58] = make_bar(
            "M5", 58, close=previous_close,
            high=previous_close + D("0.60"), low=previous_close - D("0.40"),
        )
        bars[59] = make_bar(
            "M5", 59, close=previous_close - D("0.50"),
            high=previous_close + D("0.20"), low=previous_close - D("0.60"),
        )
    return tuple(bars)


def h1_structure(side: str = "buy") -> tuple[ClosedBar, ...]:
    centers = [
        100, 101, 105, 102, 98, 101, 107, 103, 100, 103,
        109, 105, 102, 105, 111, 107, 104, 106, 108, 109,
    ]
    if side == "sell":
        centers = [300 - value for value in centers]
    return tuple(
        make_bar("H1", index, close=D(value), high=D(value) + D("0.80"), low=D(value) - D("0.80"))
        for index, value in enumerate(centers)
    )


def context(m5: tuple[ClosedBar, ...], **changes) -> PA01Context:
    values = dict(
        cutoff_utc=m5[-1].available_at_utc,
        symbol="XAUUSD.fixture",
        feed_id="fixture-feed",
        spread_price=D("0.05"),
        market_open=True,
        price_stale=False,
        news_blocked=False,
        has_exposure=False,
        has_pending=False,
        ai_enabled=False,
    )
    values.update(changes)
    return PA01Context(**values)


@pytest.mark.parametrize("side", ["buy", "sell"])
def test_pa01_symmetric_setup_is_evidence_not_an_order(side):
    m5 = m5_trend(side)
    result = evaluate_pa01(context(m5), m5_bars=m5, h1_bars=h1_structure(side))
    assert result.action == side
    assert result.reason_code == "SETUP_CONFIRMED"
    assert result.blocked_reason is None
    assert result.features.structure == ("bullish" if side == "buy" else "bearish")
    assert result.features.adx14 >= 20
    assert D("0.50") <= result.features.stop_distance_atr <= D("2.00")
    assert result.parameter_hash == PARAMETER_HASH
    assert result.ai_enabled is False
    assert result.execution_parameters.order_created is False
    assert result.execution_parameters.risk_admitted is False
    assert result.expires_at_utc - result.confirmed_at_utc == timedelta(seconds=30)
    assert result.formed_at_utc == m5[-1].close_time_utc
    assert result.confirmed_at_utc == m5[-1].available_at_utc
    assert 2 <= len(result.evidence_ids) <= 6


def test_future_rows_cannot_change_earlier_decision_or_confirm_pivot():
    m5 = m5_trend()
    h1 = h1_structure()
    cutoff = context(m5)
    expected = evaluate_pa01(cutoff, m5_bars=m5, h1_bars=h1)
    future_m5 = make_bar("M5", 60, close=D("1.00"), high=D("1.10"), low=D("0.90"))
    future_h1 = make_bar("H1", 60, close=D("1000"), high=D("1001"), low=D("999"))
    observed = evaluate_pa01(
        cutoff, m5_bars=(*m5, future_m5), h1_bars=(*h1, future_h1)
    )
    assert observed == expected

    bars = h1[:5]
    assert not any(item.evidence_id == "h1-2" for item in pivots(bars[:4]))
    pivot = next(item for item in pivots(bars) if item.evidence_id == "h1-2")
    assert pivot.formed_at_utc == bars[2].close_time_utc
    assert pivot.confirmed_at_utc == bars[4].available_at_utc


def test_exact_indicator_initialization_reference_values():
    values = tuple(map(D, ("1", "2", "3", "4", "5")))
    assert ema(values, 3) == (None, None, D("2"), D("3"), D("4"))
    assert wilder(values, 3) == (
        None, None, D("2"),
        D("2.6666666666666666666666666666666666666666666666667"),
        D("3.4444444444444444444444444444444444444444444444443"),
    )

    monotonic = tuple(make_bar("M5", index, close=D("100") + index) for index in range(30))
    assert atr(monotonic)[13] == D("1.3571428571428571428571428571428571428571428571429")
    assert adx(monotonic)[25] is None
    assert adx(monotonic)[26] == D("100")
    flat = tuple(
        make_bar("M5", index, close=D("100"), high=D("100"), low=D("100"))
        for index in range(30)
    )
    assert atr(flat)[-1] == 0
    assert adx(flat)[-1] == 0


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"market_open": False}, "MARKET_CLOSED"),
        ({"price_stale": True}, "STALE_PRICE"),
        ({"news_blocked": True}, "NEWS_PAUSE"),
        ({"spread_price": D("10")}, "SPREAD_CAP"),
        ({"has_exposure": True}, "EXPOSURE_EXISTS"),
        ({"has_pending": True}, "PENDING_EXISTS"),
    ],
)
def test_deterministic_safety_blockers(changes, reason):
    m5 = m5_trend()
    result = evaluate_pa01(context(m5, **changes), m5_bars=m5, h1_bars=h1_structure())
    assert result.action == "block"
    assert result.reason_code == reason
    assert result.blocked_reason == reason


def test_unexplained_gap_blocks_and_scheduled_close_gap_is_preserved():
    m5 = [make_bar("M5", -1, close=D("99.95")), *m5_trend()]
    del m5[41]
    shifted = evaluate_pa01(context(tuple(m5)), m5_bars=tuple(m5), h1_bars=h1_structure())
    assert (shifted.action, shifted.reason_code) == ("block", "DATA_GAP")
    m5[41] = m5[41].model_copy(update={"gap_reason_before": "market_closed"})
    admitted = evaluate_pa01(context(tuple(m5)), m5_bars=tuple(m5), h1_bars=h1_structure())
    assert admitted.action == "buy"


def test_warmup_structure_trend_setup_and_stop_fail_as_wait_not_trade():
    m5 = m5_trend()
    warmup = evaluate_pa01(context(m5[:40]), m5_bars=m5[:40], h1_bars=h1_structure())
    assert (warmup.action, warmup.reason_code) == ("wait", "INSUFFICIENT_WARMUP")
    incomplete_h1 = tuple(make_bar("H1", index, close=D("100") + index) for index in range(12))
    incomplete = evaluate_pa01(context(m5), m5_bars=m5, h1_bars=incomplete_h1)
    assert (incomplete.action, incomplete.reason_code) == ("wait", "STRUCTURE_INCOMPLETE")

    flat = tuple(make_bar("M5", index, close=D("100")) for index in range(60))
    filtered = evaluate_pa01(context(flat), m5_bars=flat, h1_bars=h1_structure())
    assert (filtered.action, filtered.reason_code) == ("wait", "TREND_FILTER")

    no_breakout = list(m5)
    no_breakout[-1] = make_bar(
        "M5", 59, close=no_breakout[-2].close,
        high=no_breakout[-2].high, low=no_breakout[-2].low,
    )
    absent = evaluate_pa01(
        context(tuple(no_breakout)), m5_bars=tuple(no_breakout), h1_bars=h1_structure()
    )
    assert (absent.action, absent.reason_code) == ("wait", "NO_PULLBACK_BREAKOUT")

    wide = list(m5)
    wide[-2] = make_bar(
        "M5", 58, close=wide[-2].close,
        high=wide[-2].high, low=wide[-2].close - D("5"),
    )
    skipped = evaluate_pa01(context(tuple(wide)), m5_bars=tuple(wide), h1_bars=h1_structure())
    assert (skipped.action, skipped.reason_code) == ("wait", "STOP_DISTANCE")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda bar: bar.model_copy(update={"symbol": "OTHER"}),
        lambda bar: bar.model_copy(update={"feed_id": "other-feed"}),
    ],
)
def test_cross_identity_evidence_fails_closed(mutate):
    m5 = list(m5_trend())
    m5[-1] = mutate(m5[-1])
    with pytest.raises(EvidenceUnavailable, match="PA01_EVIDENCE_UNAVAILABLE"):
        evaluate_pa01(context(tuple(m5)), m5_bars=tuple(m5), h1_bars=h1_structure())


def test_duplicate_or_revised_as_of_bar_fails_closed():
    m5 = m5_trend()
    duplicate = m5[-1].model_copy(update={"evidence_id": "revision", "source_revision": "v2"})
    with pytest.raises(EvidenceUnavailable):
        evaluate_pa01(context(m5), m5_bars=(*m5, duplicate), h1_bars=h1_structure())


@pytest.mark.parametrize(
    "change",
    [
        {"open": "100.00"},
        {"open_time_utc": BASE.replace(tzinfo=None)},
        {"available_at_utc": BASE + timedelta(seconds=M5_SECONDS - 1)},
        {"low": D("101"), "close": D("100")},
        {"open": D("100.001")},
        {"gap_reason_before": "unknown"},
    ],
)
def test_malformed_forming_or_inexact_bar_is_rejected(change):
    values = dict(
        evidence_id="bar", feed_id="fixture-feed", source_revision="v1", symbol="XAUUSD.fixture",
        timeframe="M5", open_time_utc=BASE,
        available_at_utc=BASE + timedelta(seconds=M5_SECONDS + 1),
        open=D("100"), high=D("101"), low=D("99"), close=D("100"), tick_size=D("0.01"), digits=2,
        gap_reason_before="none",
    )
    values.update(change)
    with pytest.raises(ValidationError):
        ClosedBar(**values)


def test_kernel_has_no_io_ai_random_clock_or_execution_authority():
    source = Path("services/worker/src/sochron_worker/pa01.py").read_text()
    for forbidden in (
        "import httpx", "import requests", "import os", "import random", "datetime.now",
        "supabase", "OrderSend", "ExecutionService", "service_role", "open(", "sqlite3",
    ):
        assert forbidden not in source
    assert "order_created: Literal[False]" in source
    assert "risk_admitted: Literal[False]" in source
