"""random_entry_baseline(): BASELINE_RUNS random-entry runs per variant (H001 section 7, contract D1-D5).

The seed comes from the base record, random.Random(int(base_run_id[:15], 16)), so nobody chooses it; the
generator is looked up on the random module at call time and drawn with randrange only. Every random
trade is filled by backtest.simulate_trade, entered on a bar strategy.entry_blockers allows and held for
a hold drawn from the variant's strategy-timed exits, its own stop cutting it short.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, Overflow, localcontext
from pathlib import Path

from sochron import backtest
from sochron.backtest import Result, Rollover, Side, SizedLots, Sizer, Trade
from sochron.core import Bar
from sochron.costs import CONTEXT, CostModel
from sochron.strategy import H001Params, entry_blockers, indicators
from sochron.timebase import TimeRule

from . import registry as registry_module  # the argument `registry` is the file path
from .inputs import (
    M15,
    check_against_base,
    check_bars,
    check_budget,
    check_dataset,
    check_types,
    check_values,
    find_base,
    holdout_guard,
    record_failure,
    started_record,
)
from .model import BASELINE_RUNS, BaselineSummary, Dataset, ResearchError, exact, too_large
from .records import RunRecord
from .stats import mean_in_order, percentile, summarize

_SIDES: tuple[Side, Side] = ("long", "short")
_HALF = Decimal("0.5")


@dataclass(frozen=True)
class BaselineResult:
    """Every round's expectancy in round order, their summary and the ok record (trades are not kept)."""

    expectancies_r: tuple[Decimal, ...]
    summary: BaselineSummary
    record: RunRecord


@dataclass(frozen=True)
class _Plan:
    """What the rounds need, all checked before the started line."""

    m1: Sequence[Bar]
    bars15: M15
    first: list[int]
    bar_of: list[int]
    eligible: tuple[int, ...]
    stops: dict[int, Decimal]
    holds: tuple[int, ...]
    trades: int


def _median(values: Sequence[int]) -> int:
    return int(percentile([Decimal(value) for value in values], _HALF))


def _mean(values: Sequence[int]) -> Decimal:
    mean = mean_in_order([Decimal(value) for value in values])
    if mean is None:  # not reached: the variant has trades and every round makes trades
        raise ResearchError("a mean needs at least one value")
    return mean


def _plan(m1: Sequence[Bar], bars15: M15, m15: Sequence[object], params: H001Params, rule: TimeRule,
          variant: Result) -> _Plan:
    """Steps 2-4: the bar checks, the variant's trade times and holds, and the eligible bars."""
    first, bar_of = check_bars(m1, bars15, rule)
    index = {bar.time_raw: position for position, bar in enumerate(m1)}
    for number, trade in enumerate(variant.trades):
        if trade.entry_time_raw not in index or trade.exit_time_raw not in index:
            raise ResearchError(f"variant trade {number} has a time that is no M1 of m1")
    holds = tuple(index[trade.exit_time_raw] - index[trade.entry_time_raw] for trade in variant.trades
                  if trade.exit_reason in ("signal", "end_of_data") or trade.ambiguous)
    if not holds:
        raise ResearchError("the variant has no trade with a strategy-timed exit to draw a hold from")
    rows = indicators(m15, params)
    eligible = tuple(t for t in range(len(bars15) - 1) if not entry_blockers(rows[t], bars15[t + 1][0].time_utc))
    if len(eligible) < len(variant.trades):
        raise ResearchError(f"{len(eligible)} eligible bars for {len(variant.trades)} trades a round")
    stops: dict[int, Decimal] = {}
    for t in eligible:
        atr = rows[t].atr
        if atr is None:  # not reached: entry_blockers blocks a bar without ATR (atr_zero)
            raise ResearchError(f"bar {t} has no ATR")
        try:
            with localcontext(CONTEXT):
                stops[t] = params.k * atr  # D4: the stop distance decide would give
        except Overflow as error:
            raise too_large(error) from error
    return _Plan(m1, bars15, first, bar_of, eligible, stops, holds, len(variant.trades))


def _round(plan: _Plan, rng: random.Random, sizer: Sizer, equity: Decimal, model: CostModel,
           rollover: Rollover) -> list[Trade]:
    """Step 7, one round: K trades on distinct bars, drawn in the contract's order."""
    m1 = plan.m1
    pool = list(plan.eligible)
    trades: list[Trade] = []
    while len(trades) < plan.trades:
        if not pool:
            raise ResearchError("the round ran out of eligible bars before it had its trades")
        t = pool.pop(rng.randrange(len(pool)))
        stop_distance = plan.stops[t]
        sized = exact(sizer(equity, stop_distance), SizedLots, "the sizer's result")
        lots = sized.lots
        if lots is None:
            continue
        side = _SIDES[rng.randrange(2)]
        hold = plan.holds[rng.randrange(len(plan.holds))]
        entry_index = plan.first[t + 1]
        planned = entry_index + max(hold, 1)
        exit_index = planned if planned < len(m1) else None
        last = len(m1) - 1 if exit_index is None else exit_index
        flags: frozenset[str] = frozenset().union(*(plan.bars15[u][1] for u in range(t, plan.bar_of[last] + 1)))
        trades.append(backtest.simulate_trade(
            m1, entry_index, side, stop_distance, lots, model, rollover, risk_money=sized.risk_money,
            actual_risk=sized.actual_risk, exit_index=exit_index, data_flags=flags))
    return trades


def random_entry_baseline(
    m1: Sequence[Bar],
    m15: Sequence[object],
    params: H001Params,
    model: CostModel,
    sizer: Sizer,
    equity: Decimal,
    rule: TimeRule,
    rollover: Rollover,
    variant: Result,
    *,
    base_run_id: str,
    dataset: Dataset,
    code_commit: str,
    sizer_label: str,
    registry: Path,
) -> BaselineResult:
    """BASELINE_RUNS random-entry rounds of the variant's trade count, recorded as random_entry."""
    path = registry
    holdout_guard(m1, m15, dataset)
    bars, bars15 = check_types(m1, m15, params, model, sizer, equity, rule, rollover, dataset, code_commit,
                               sizer_label, path)
    exact(variant, Result, "variant")
    exact(base_run_id, str, "base_run_id")
    check_values(model, equity, code_commit, sizer_label, path, "1")
    check_dataset(dataset, bars)
    records = registry_module.read_records(path)
    base = find_base(records, base_run_id, params.variant)
    started = started_record(seq=len(records) + 1, purpose="random_entry", params=params, base_run_id=base_run_id,
                             model=model, equity=equity, rule=rule, rollover=rollover, dataset=dataset,
                             code_commit=code_commit, sizer_label=sizer_label)
    check_against_base(started, base)
    if summarize(variant, rule) != base.summary:
        raise ResearchError(f"the variant is not the result of the base (seq {base.seq}): its summary differs")
    check_budget(records, started)
    plan = _plan(bars, bars15, m15, params, rule, variant)
    seed = int(base_run_id[:15], 16)
    rng = random.Random(seed)
    registry_module.append_record(path, started)
    try:
        expectancies: list[Decimal] = []
        holds: list[int] = []
        index = {bar.time_raw: position for position, bar in enumerate(bars)}
        for _ in range(BASELINE_RUNS):
            trades = _round(plan, rng, sizer, equity, model, rollover)
            expectancy = mean_in_order([trade.r for trade in trades])  # the sum in trade order / K
            if expectancy is None:  # not reached: a round has K >= 1 trades
                raise ResearchError("a round without trades")
            expectancies.append(expectancy)
            holds.extend(index[trade.exit_time_raw] - index[trade.entry_time_raw] for trade in trades)
        variant_holds = [index[trade.exit_time_raw] - index[trade.entry_time_raw] for trade in variant.trades]
        mean = mean_in_order(expectancies)
        if mean is None:  # not reached: BASELINE_RUNS rounds
            raise ResearchError("no rounds")
        summary = BaselineSummary(
            runs=BASELINE_RUNS, trades_per_run=plan.trades, seed=seed, mean_r=mean,
            p05_r=percentile(expectancies, Decimal("0.05")), p50_r=percentile(expectancies, _HALF),
            p95_r=percentile(expectancies, Decimal("0.95")), variant_mean_hold_m1=_mean(variant_holds),
            variant_median_hold_m1=_median(variant_holds), baseline_mean_hold_m1=_mean(holds),
            baseline_median_hold_m1=_median(holds))
        ok = replace(started, seq=started.seq + 1, status="ok", started_seq=started.seq, baseline=summary)
        registry_module.append_record(path, ok)
    except BaseException as error:  # KeyboardInterrupt and disk errors included (step 9)
        record_failure(path, started, error)
        raise
    return BaselineResult(tuple(expectancies), summary, ok)
