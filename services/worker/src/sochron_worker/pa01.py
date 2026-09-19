"""Pure PA01-v1 decision kernel; no I/O, persistence, risk or execution authority."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
from itertools import pairwise
from typing import Literal, Self

from pydantic import AwareDatetime, Field, StrictBool, StrictInt, field_validator, model_validator
from sochron1k.models import StrictModel
from sochron1k.telemetry import FiniteDecimal

STRATEGY_VERSION = "PA01-v1"
PARAMETER_VERSION = "PA01-v1.0.0"
M5_SECONDS = 300
H1_SECONDS = 3600
MAX_WINDOW = 100
MIN_M5 = 60
MIN_H1 = 12
EMA_FAST = 20
EMA_SLOW = 50
WILDER_PERIOD = 14
ADX_MINIMUM = Decimal("20")
STOP_BUFFER_ATR = Decimal("0.20")
STOP_MIN_ATR = Decimal("0.50")
STOP_MAX_ATR = Decimal("2.00")
SPREAD_MAX_ATR = Decimal("0.10")
ENTRY_DRIFT_MAX_ATR = Decimal("0.20")
TARGET_R = Decimal("2")
EXPIRY_SECONDS = 30
TIME_EXIT_BARS = 12
MAX_MARKET_CLOSE_GAP_SECONDS = 72 * 3600

PARAMETERS = {
    "strategy_version": STRATEGY_VERSION,
    "parameter_version": PARAMETER_VERSION,
    "ai_enabled": False,
    "signal_timeframe": "M5",
    "structure_timeframe": "H1",
    "max_window": MAX_WINDOW,
    "min_m5": MIN_M5,
    "min_h1": MIN_H1,
    "pivot_left": 2,
    "pivot_right": 2,
    "ema_fast": EMA_FAST,
    "ema_slow": EMA_SLOW,
    "wilder_period": WILDER_PERIOD,
    "adx_minimum": "20",
    "stop_buffer_atr": "0.20",
    "stop_min_atr": "0.50",
    "stop_max_atr": "2.00",
    "spread_max_atr": "0.10",
    "entry_drift_max_atr": "0.20",
    "target_r": "2",
    "expiry_seconds": EXPIRY_SECONDS,
    "time_exit_bars": TIME_EXIT_BARS,
    "max_market_close_gap_seconds": MAX_MARKET_CLOSE_GAP_SECONDS,
    "atr_seed": "mean-first-14-tr-including-first-range",
    "adx_seed": "mean-dx-indices-13-through-26-first-dm-zero",
}
PARAMETER_HASH = hashlib.sha256(
    json.dumps(PARAMETERS, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()

Timeframe = Literal["M5", "H1"]
DecisionAction = Literal["buy", "sell", "wait", "block"]
Structure = Literal["bullish", "bearish", "mixed", "incomplete"]
ReasonCode = Literal[
    "SETUP_CONFIRMED",
    "INSUFFICIENT_WARMUP",
    "STRUCTURE_INCOMPLETE",
    "STRUCTURE_MIXED",
    "TREND_FILTER",
    "NO_PULLBACK_BREAKOUT",
    "STOP_DISTANCE",
    "MARKET_CLOSED",
    "STALE_PRICE",
    "DATA_GAP",
    "NEWS_PAUSE",
    "SPREAD_CAP",
    "EXPOSURE_EXISTS",
    "PENDING_EXISTS",
]


class EvidenceUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("PA01_EVIDENCE_UNAVAILABLE")


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _safe_text(value: str) -> str:
    if not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("unsafe text")
    return value


class ClosedBar(StrictModel):
    evidence_id: str = Field(min_length=1, max_length=128)
    feed_id: str = Field(min_length=1, max_length=128)
    source_revision: str = Field(min_length=1, max_length=128)
    symbol: str = Field(min_length=1, max_length=32, pattern=r"^[^\s]+$")
    price_basis: Literal["bid"] = "bid"
    timeframe: Timeframe
    open_time_utc: AwareDatetime
    available_at_utc: AwareDatetime
    open: FiniteDecimal = Field(gt=0)
    high: FiniteDecimal = Field(gt=0)
    low: FiniteDecimal = Field(gt=0)
    close: FiniteDecimal = Field(gt=0)
    tick_size: FiniteDecimal = Field(gt=0)
    digits: StrictInt = Field(ge=0, le=10)
    gap_reason_before: Literal["none", "market_closed"] = "none"

    @field_validator("open", "high", "low", "close", "tick_size", mode="before")
    @classmethod
    def exact_decimals(cls, value: object) -> object:
        if not isinstance(value, Decimal):
            raise ValueError("Decimal evidence required")
        return value

    @field_validator("evidence_id", "feed_id", "source_revision")
    @classmethod
    def safe_identifiers(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("open_time_utc", "available_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return _utc(value)

    @model_validator(mode="after")
    def exact_closed_bar(self) -> Self:
        period = M5_SECONDS if self.timeframe == "M5" else H1_SECONDS
        epoch = int(self.open_time_utc.timestamp())
        close_time = self.open_time_utc + timedelta(seconds=period)
        if epoch % period or self.available_at_utc < close_time:
            raise ValueError("bar is misaligned or not closed")
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
        seconds = M5_SECONDS if self.timeframe == "M5" else H1_SECONDS
        return self.open_time_utc + timedelta(seconds=seconds)


class PA01Context(StrictModel):
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


class PivotEvidence(StrictModel):
    kind: Literal["high", "low"]
    price: Decimal
    evidence_id: str
    formed_at_utc: AwareDatetime
    confirmed_at_utc: AwareDatetime


class PA01Features(StrictModel):
    structure: Structure
    ema20: Decimal | None
    ema50: Decimal | None
    previous_ema20: Decimal | None
    atr14: Decimal | None
    adx14: Decimal | None
    spread_cap: Decimal | None
    proposed_stop: Decimal | None
    stop_distance_at_close: Decimal | None
    stop_distance_atr: Decimal | None
    latest_swing_highs: tuple[PivotEvidence, ...] = ()
    latest_swing_lows: tuple[PivotEvidence, ...] = ()


class PA01ExecutionParameters(StrictModel):
    next_tick_entry_required: Literal[True] = True
    max_entry_drift_atr: Decimal = ENTRY_DRIFT_MAX_ATR
    stop_buffer_atr: Decimal = STOP_BUFFER_ATR
    stop_min_atr: Decimal = STOP_MIN_ATR
    stop_max_atr: Decimal = STOP_MAX_ATR
    target_r: Decimal = TARGET_R
    time_exit_m5_bars: Literal[12] = TIME_EXIT_BARS
    signal_expiry_seconds: Literal[30] = EXPIRY_SECONDS
    order_created: Literal[False] = False
    risk_admitted: Literal[False] = False


class PA01Decision(StrictModel):
    strategy_version: Literal["PA01-v1"] = STRATEGY_VERSION
    parameter_version: Literal["PA01-v1.0.0"] = PARAMETER_VERSION
    parameter_hash: str = PARAMETER_HASH
    ai_enabled: Literal[False] = False
    action: DecisionAction
    reason_code: ReasonCode
    blocked_reason: str | None
    setup_id: str
    decision_id: str
    symbol: str
    data_cutoff_utc: AwareDatetime
    formed_at_utc: AwareDatetime
    confirmed_at_utc: AwareDatetime
    expires_at_utc: AwareDatetime
    dataset_hash: str
    evidence_ids: tuple[str, ...] = Field(max_length=8)
    features: PA01Features
    execution_parameters: PA01ExecutionParameters = PA01ExecutionParameters()

    @model_validator(mode="after")
    def action_semantics(self) -> Self:
        if (self.action == "block") != (self.blocked_reason is not None):
            raise ValueError("blocked reason must match BLOCK")
        if self.action in {"buy", "sell"} and self.reason_code != "SETUP_CONFIRMED":
            raise ValueError("confirmed setup reason required")
        return self


def ema(values: tuple[Decimal, ...], period: int) -> tuple[Decimal | None, ...]:
    if type(period) is not int or period < 2:
        raise ValueError("invalid EMA period")
    output: list[Decimal | None] = [None] * len(values)
    if len(values) < period:
        return tuple(output)
    with localcontext() as context:
        context.prec = 50
        current = sum(values[:period], Decimal()) / Decimal(period)
        output[period - 1] = +current
        alpha = Decimal(2) / Decimal(period + 1)
        for index in range(period, len(values)):
            current = (values[index] - current) * alpha + current
            output[index] = +current
    return tuple(output)


def _true_ranges(bars: tuple[ClosedBar, ...]) -> tuple[Decimal, ...]:
    result: list[Decimal] = []
    for index, bar in enumerate(bars):
        previous = bars[index - 1].close if index else bar.close
        result.append(max(bar.high - bar.low, abs(bar.high - previous), abs(bar.low - previous)))
    return tuple(result)


def wilder(values: tuple[Decimal, ...], period: int) -> tuple[Decimal | None, ...]:
    if type(period) is not int or period < 2:
        raise ValueError("invalid Wilder period")
    output: list[Decimal | None] = [None] * len(values)
    if len(values) < period:
        return tuple(output)
    with localcontext() as context:
        context.prec = 50
        current = sum(values[:period], Decimal()) / Decimal(period)
        output[period - 1] = +current
        for index in range(period, len(values)):
            current = (current * Decimal(period - 1) + values[index]) / Decimal(period)
            output[index] = +current
    return tuple(output)


def atr(bars: tuple[ClosedBar, ...], period: int = WILDER_PERIOD) -> tuple[Decimal | None, ...]:
    return wilder(_true_ranges(bars), period)


def adx(bars: tuple[ClosedBar, ...], period: int = WILDER_PERIOD) -> tuple[Decimal | None, ...]:
    if len(bars) < 2:
        return tuple([None] * len(bars))
    true_ranges = _true_ranges(bars)
    plus_dm = [Decimal()] * len(bars)
    minus_dm = [Decimal()] * len(bars)
    for index in range(1, len(bars)):
        upward = bars[index].high - bars[index - 1].high
        downward = bars[index - 1].low - bars[index].low
        plus_dm[index] = upward if upward > downward and upward > 0 else Decimal()
        minus_dm[index] = downward if downward > upward and downward > 0 else Decimal()
    smooth_tr = wilder(true_ranges, period)
    smooth_plus = wilder(tuple(plus_dm), period)
    smooth_minus = wilder(tuple(minus_dm), period)
    dx: list[Decimal | None] = [None] * len(bars)
    with localcontext() as context:
        context.prec = 50
        for index in range(period - 1, len(bars)):
            denominator = smooth_tr[index]
            if denominator is None or denominator == 0:
                dx[index] = Decimal()
                continue
            plus_di = Decimal(100) * smooth_plus[index] / denominator
            minus_di = Decimal(100) * smooth_minus[index] / denominator
            total = plus_di + minus_di
            dx[index] = Decimal() if total == 0 else Decimal(100) * abs(plus_di - minus_di) / total
        output: list[Decimal | None] = [None] * len(bars)
        first = period - 1
        seed_end = first + period
        if len(bars) < seed_end:
            return tuple(output)
        current = sum(
            (value for value in dx[first:seed_end] if value is not None), Decimal()
        ) / Decimal(period)
        output[seed_end - 1] = +current
        for index in range(seed_end, len(bars)):
            current = (current * Decimal(period - 1) + dx[index]) / Decimal(period)
            output[index] = +current
    return tuple(output)


def pivots(bars: tuple[ClosedBar, ...]) -> tuple[PivotEvidence, ...]:
    result: list[PivotEvidence] = []
    for index in range(2, len(bars) - 2):
        bar = bars[index]
        neighbours = bars[index - 2 : index] + bars[index + 1 : index + 3]
        confirmed = bars[index + 2].available_at_utc
        if all(bar.high > other.high for other in neighbours):
            result.append(
                PivotEvidence(
                    kind="high",
                    price=bar.high,
                    evidence_id=bar.evidence_id,
                    formed_at_utc=bar.close_time_utc,
                    confirmed_at_utc=confirmed,
                )
            )
        if all(bar.low < other.low for other in neighbours):
            result.append(
                PivotEvidence(
                    kind="low",
                    price=bar.low,
                    evidence_id=bar.evidence_id,
                    formed_at_utc=bar.close_time_utc,
                    confirmed_at_utc=confirmed,
                )
            )
    return tuple(result)


def _canonical_bar(bar: ClosedBar) -> dict[str, object]:
    return {
        "evidence_id": bar.evidence_id,
        "feed_id": bar.feed_id,
        "source_revision": bar.source_revision,
        "symbol": bar.symbol,
        "price_basis": bar.price_basis,
        "timeframe": bar.timeframe,
        "open_time_utc": bar.open_time_utc.isoformat(),
        "available_at_utc": bar.available_at_utc.isoformat(),
        "open": _decimal_text(bar.open),
        "high": _decimal_text(bar.high),
        "low": _decimal_text(bar.low),
        "close": _decimal_text(bar.close),
        "tick_size": _decimal_text(bar.tick_size),
        "digits": bar.digits,
        "gap_reason_before": bar.gap_reason_before,
    }


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _as_of(
    bars: tuple[ClosedBar, ...], context: PA01Context, timeframe: Timeframe
) -> tuple[ClosedBar, ...]:
    selected = tuple(
        sorted(
            (
                bar
                for bar in bars
                if bar.available_at_utc <= context.cutoff_utc
                and bar.close_time_utc <= context.cutoff_utc
            ),
            key=lambda bar: (bar.open_time_utc, bar.available_at_utc, bar.evidence_id),
        )
    )
    if any(
        bar.timeframe != timeframe
        or bar.symbol != context.symbol
        or bar.feed_id != context.feed_id
        for bar in selected
    ):
        raise EvidenceUnavailable()
    times = [bar.open_time_utc for bar in selected]
    if len(set(times)) != len(times) or len({bar.evidence_id for bar in selected}) != len(selected):
        raise EvidenceUnavailable()
    if selected:
        grid = {(bar.tick_size, bar.digits) for bar in selected}
        revisions = {(bar.open_time_utc, bar.source_revision) for bar in selected}
        if len(grid) != 1 or len(revisions) != len(selected):
            raise EvidenceUnavailable()
    return selected[-MAX_WINDOW:]


def _has_gap(bars: tuple[ClosedBar, ...], seconds: int) -> bool:
    for previous, current in pairwise(bars):
        elapsed = int((current.open_time_utc - previous.open_time_utc).total_seconds())
        if elapsed == seconds:
            if current.gap_reason_before != "none":
                raise EvidenceUnavailable()
        elif (
            elapsed <= seconds
            or elapsed > MAX_MARKET_CLOSE_GAP_SECONDS
            or current.gap_reason_before != "market_closed"
        ):
            return True
    return False


def _structure(
    h1: tuple[ClosedBar, ...],
) -> tuple[Structure, tuple[PivotEvidence, ...], tuple[PivotEvidence, ...]]:
    all_pivots = pivots(h1)
    highs = tuple(item for item in all_pivots if item.kind == "high")[-2:]
    lows = tuple(item for item in all_pivots if item.kind == "low")[-2:]
    if len(highs) < 2 or len(lows) < 2:
        return "incomplete", highs, lows
    if highs[1].price > highs[0].price and lows[1].price > lows[0].price:
        return "bullish", highs, lows
    if highs[1].price < highs[0].price and lows[1].price < lows[0].price:
        return "bearish", highs, lows
    return "mixed", highs, lows


def evaluate_pa01(
    context: PA01Context,
    *,
    m5_bars: tuple[ClosedBar, ...],
    h1_bars: tuple[ClosedBar, ...],
) -> PA01Decision:
    """Evaluate one as-of cutoff. The caller owns scheduling, persistence and admission."""
    try:
        m5 = _as_of(m5_bars, context, "M5")
        h1 = _as_of(h1_bars, context, "H1")
        if len(m5) < 2:
            raise EvidenceUnavailable()
        latest, previous = m5[-1], m5[-2]
        formed = latest.close_time_utc
        data_cutoff = max(bar.available_at_utc for bar in m5 + h1)
        confirmed = data_cutoff
        expires = confirmed + timedelta(seconds=EXPIRY_SECONDS)
        grids = {(bar.tick_size, bar.digits) for bar in m5 + h1}
        if len(grids) != 1:
            raise EvidenceUnavailable()
        tick_size = m5[-1].tick_size
        spread_num, spread_den = context.spread_price.as_integer_ratio()
        tick_num, tick_den = tick_size.as_integer_ratio()
        if spread_num * tick_den % (spread_den * tick_num):
            raise EvidenceUnavailable()
        dataset_hash = _digest([_canonical_bar(bar) for bar in m5 + h1])
        setup_id = "setup-" + _digest(
            [STRATEGY_VERSION, context.symbol, latest.open_time_utc.isoformat()]
        )[:32]

        structure, swing_highs, swing_lows = _structure(h1)
        closes = tuple(bar.close for bar in m5)
        ema20_values, ema50_values = ema(closes, EMA_FAST), ema(closes, EMA_SLOW)
        atr_values, adx_values = atr(m5), adx(m5)
        ema20, ema50 = ema20_values[-1], ema50_values[-1]
        previous_ema20 = ema20_values[-2]
        atr14, adx14 = atr_values[-1], adx_values[-1]
        spread_cap = atr14 * SPREAD_MAX_ATR if atr14 is not None else None
        proposed_stop = None
        stop_distance = None
        stop_distance_atr = None

        insufficient = (
            len(m5) < MIN_M5
            or len(h1) < MIN_H1
            or None in {ema20, ema50, previous_ema20, atr14, adx14}
        )
        gap = _has_gap(m5, M5_SECONDS) or _has_gap(h1, H1_SECONDS)
        action: DecisionAction = "wait"
        reason: ReasonCode
        blocked_reason = None

        if not context.market_open:
            action, reason = "block", "MARKET_CLOSED"
        elif context.price_stale:
            action, reason = "block", "STALE_PRICE"
        elif gap:
            action, reason = "block", "DATA_GAP"
        elif context.news_blocked:
            action, reason = "block", "NEWS_PAUSE"
        elif context.has_exposure:
            action, reason = "block", "EXPOSURE_EXISTS"
        elif context.has_pending:
            action, reason = "block", "PENDING_EXISTS"
        elif insufficient:
            reason = "INSUFFICIENT_WARMUP"
        elif context.spread_price > spread_cap:
            action, reason = "block", "SPREAD_CAP"
        elif structure == "incomplete":
            reason = "STRUCTURE_INCOMPLETE"
        elif structure == "mixed":
            reason = "STRUCTURE_MIXED"
        elif adx14 < ADX_MINIMUM or (
            structure == "bullish" and not ema20 > ema50
        ) or (structure == "bearish" and not ema20 < ema50):
            reason = "TREND_FILTER"
        else:
            buy = (
                structure == "bullish"
                and previous.low <= previous_ema20
                and latest.close > previous.high
            )
            sell = (
                structure == "bearish"
                and previous.high >= previous_ema20
                and latest.close < previous.low
            )
            if not buy and not sell:
                reason = "NO_PULLBACK_BREAKOUT"
            else:
                if buy:
                    proposed_stop = min(previous.low, latest.low) - STOP_BUFFER_ATR * atr14
                    stop_distance = latest.close - proposed_stop
                else:
                    proposed_stop = max(previous.high, latest.high) + STOP_BUFFER_ATR * atr14
                    stop_distance = proposed_stop - latest.close
                stop_distance_atr = stop_distance / atr14 if atr14 > 0 else None
                if (
                    stop_distance_atr is None
                    or stop_distance_atr < STOP_MIN_ATR
                    or stop_distance_atr > STOP_MAX_ATR
                ):
                    reason = "STOP_DISTANCE"
                else:
                    action, reason = ("buy" if buy else "sell"), "SETUP_CONFIRMED"

        if action == "block":
            blocked_reason = reason
        evidence = [previous.evidence_id, latest.evidence_id]
        evidence.extend(item.evidence_id for item in swing_highs + swing_lows)
        evidence_ids = tuple(dict.fromkeys(evidence))
        features = PA01Features(
            structure=structure,
            ema20=ema20,
            ema50=ema50,
            previous_ema20=previous_ema20,
            atr14=atr14,
            adx14=adx14,
            spread_cap=spread_cap,
            proposed_stop=proposed_stop,
            stop_distance_at_close=stop_distance,
            stop_distance_atr=stop_distance_atr,
            latest_swing_highs=swing_highs,
            latest_swing_lows=swing_lows,
        )
        decision_id = "decision-" + _digest(
            [PARAMETER_HASH, dataset_hash, setup_id, action, reason, confirmed.isoformat()]
        )[:32]
        return PA01Decision(
            action=action,
            reason_code=reason,
            blocked_reason=blocked_reason,
            setup_id=setup_id,
            decision_id=decision_id,
            symbol=context.symbol,
            data_cutoff_utc=data_cutoff,
            formed_at_utc=formed,
            confirmed_at_utc=confirmed,
            expires_at_utc=expires,
            dataset_hash=dataset_hash,
            evidence_ids=evidence_ids,
            features=features,
        )
    except (ValueError, TypeError, ArithmeticError, OverflowError, RecursionError):
        raise EvidenceUnavailable() from None
