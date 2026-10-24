"""evaluate(): the ten conditions of H001 section 8 from consistent registry records (contract D14).

A missing stress, long-only or random-entry record, or no robustness records, fails only the rows that
need it, so such a structure can be "stop" or "insufficient" but never "go" (F27, F34, F37).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from .inputs import different_field, param_pairs, params_of
from .model import HOLDOUT_CUTOFF_UTC, Dataset, ResearchError, Summary, exact, exact_optional
from .records import RunRecord, stress_factor
from .robustness import neighbours

Verdict = Literal["go", "stop", "insufficient"]
_TEN_CENTS = Decimal("0.10")
_MAX_DRAWDOWN = Decimal("24")
_MIN_TRADES = 100


@dataclass(frozen=True)
class Check:
    """One row: the measured value and the threshold as text, and whether the row passes."""

    name: str
    value: str
    threshold: str
    passed: bool

    def __post_init__(self) -> None:
        for name in ("name", "value", "threshold"):
            exact(getattr(self, name), str, name)
        exact(self.passed, bool, "passed")


@dataclass(frozen=True)
class Evaluation:
    """The verdict of one structure's base and its rows; screen means data from before the holdout cutoff."""

    variant: str
    base_run_id: str
    dataset: Dataset
    screen: bool
    verdict: Verdict
    checks: tuple[Check, ...]

    def __post_init__(self) -> None:
        exact(self.variant, str, "variant")
        exact(self.base_run_id, str, "base_run_id")
        exact(self.dataset, Dataset, "dataset")
        exact(self.screen, bool, "screen")
        exact(self.verdict, str, "verdict")
        for check in exact(self.checks, tuple, "checks"):
            exact(check, Check, "a check")


def _text(value: Decimal | None) -> str:
    return "none" if value is None else str(value)


def _summary(record: RunRecord) -> Summary:
    summary = record.summary
    if summary is None:  # not reached: RunRecord gives every ok line but random_entry a summary
        raise ResearchError(f"record seq {record.seq} has no summary")
    return summary


def _check_inputs(base: RunRecord, optional: Sequence[tuple[str, RunRecord]]) -> None:
    """Every record ok and of its purpose, on this base, with the base's setup, params and stress factor."""
    if base.status != "ok" or base.purpose != "select":
        raise ResearchError("the base must be an ok select record")
    if stress_factor(base) != "1":
        raise ResearchError("the base must have stress_factor '1'")
    base_id = base.run_id
    for purpose, record in optional:
        if record.status != "ok":
            raise ResearchError(f"the {purpose} record (seq {record.seq}) is not ok")
        if record.purpose != purpose:
            raise ResearchError(f"a record of purpose {record.purpose} was given as {purpose}")
        if record.base_run_id != base_id:
            raise ResearchError(f"the {purpose} record (seq {record.seq}) has another base")
        if record.hypothesis != base.hypothesis or record.variant != base.variant:
            raise ResearchError(f"the {purpose} record (seq {record.seq}) is of another hypothesis or variant")
        name = different_field(record, base)
        if name is not None:
            raise ResearchError(f"{name} of the {purpose} record (seq {record.seq}) differs from the base")
        if purpose != "robustness" and record.params != base.params:
            raise ResearchError(f"params of the {purpose} record (seq {record.seq}) differ from the base")
        if stress_factor(record) != ("2" if purpose == "stress" else "1"):
            raise ResearchError(f"the {purpose} record (seq {record.seq}) has the wrong stress_factor")


def evaluate(base: RunRecord, stress: RunRecord | None, long_only: RunRecord | None,
             random_entry: RunRecord | None, robustness: Sequence[RunRecord]) -> Evaluation:
    """The ten rows and the verdict: row 1 failing is insufficient, all ten passing is go, else stop."""
    exact(base, RunRecord, "base")
    for name, record in (("stress", stress), ("long_only", long_only), ("random_entry", random_entry)):
        exact_optional(record, RunRecord, name)
    if not isinstance(robustness, Sequence) or isinstance(robustness, (str, bytes)):
        raise TypeError(f"robustness must be a sequence of RunRecord, not {type(robustness).__name__}")
    for index, item in enumerate(robustness):
        exact(item, RunRecord, f"robustness[{index}]")
    optional = [(name, record) for name, record in (("stress", stress), ("long_only", long_only),
                                                     ("random_entry", random_entry)) if record is not None]
    _check_inputs(base, optional + [("robustness", item) for item in robustness])
    every = neighbours(params_of(base))
    if robustness:
        valid = [param_pairs(item.params) for item in every if item.params is not None]
        if [item.params for item in robustness] != valid:
            raise ResearchError("robustness must hold one record per valid neighbour of the base, in order")
    summary = _summary(base)
    p95 = None
    if random_entry is not None:
        baseline = random_entry.baseline
        if baseline is None:  # not reached: RunRecord gives an ok random_entry line a baseline
            raise ResearchError("the random_entry record has no baseline")
        if baseline.trades_per_run != summary.trades:
            raise ResearchError("trades_per_run of the baseline is not the base's number of trades")
        p95 = baseline.p95_r
    checks = (
        _trades(summary),
        _expectancy(summary),
        _stress(None if stress is None else _summary(stress)),
        Check("max_drawdown_r", str(summary.max_drawdown_r), "24", summary.max_drawdown_r <= _MAX_DRAWDOWN),
        _robustness(len(every), [_summary(item) for item in robustness]),
        _random_entry(summary, p95),
        _top5(summary),
        _years(summary),
        _sides(summary),
        _long_only(summary, None if long_only is None else _summary(long_only)),
    )
    verdict: Verdict = "insufficient" if not checks[0].passed else "go" if all(c.passed for c in checks) else "stop"
    dataset = base.dataset
    return Evaluation(base.variant, base.run_id, dataset, dataset.period_start_utc < HOLDOUT_CUTOFF_UTC, verdict,
                      checks)


def _trades(summary: Summary) -> Check:
    return Check("trades", str(summary.trades), str(_MIN_TRADES), summary.trades >= _MIN_TRADES)


def _expectancy(summary: Summary) -> Check:
    value = summary.expectancy_r
    return Check("expectancy_1x", _text(value), "0.10", value is not None and value >= _TEN_CENTS)


def _stress(stress: Summary | None) -> Check:
    value = None if stress is None else stress.expectancy_r
    return Check("expectancy_2x", _text(value), "0", value is not None and value > 0)


def _robustness(count: int, runs: Sequence[Summary]) -> Check:
    needed = -(-8 * count // 10)  # ceil(0.8 x count) without leaving integers
    threshold = f"{needed}/{count}"
    if not runs:
        return Check("robustness", "none", threshold, False)
    passed = sum(1 for run in runs if run.expectancy_r is not None and run.expectancy_r > 0)
    return Check("robustness", f"{passed}/{count}", threshold, passed >= needed)


def _random_entry(summary: Summary, p95: Decimal | None) -> Check:
    value = summary.expectancy_r
    return Check("vs_random_entry", _text(value), _text(p95), value is not None and p95 is not None and value > p95)


def _top5(summary: Summary) -> Check:
    value = summary.top5_removed_expectancy_r
    return Check("top5_removed", _text(value), "0", value is not None and value > 0)


def _years(summary: Summary) -> Check:
    years = summary.expectancy_by_year
    text = ";".join(f"{year}:{value}" for year, value in years) or "none"
    return Check("years", text, "0", bool(years) and all(value >= 0 for _, value in years))


def _sides(summary: Summary) -> Check:
    long, short = summary.long_expectancy_r, summary.short_expectancy_r
    passed = long is not None and short is not None and long >= 0 and short >= 0
    return Check("sides", f"long:{_text(long)};short:{_text(short)}", "0", passed)


def _long_only(summary: Summary, other: Summary | None) -> Check:
    mine = summary.expectancy_r
    theirs = None if other is None else other.expectancy_r
    their_drawdown = None if other is None else other.max_drawdown_r
    value = (f"expectancy:{_text(mine)}/{_text(theirs)};"
             f"max_drawdown:{summary.max_drawdown_r}/{_text(their_drawdown)}")
    passed = (other is not None and other.trades > 0 and summary.trades > 0 and mine is not None
              and theirs is not None and (mine > theirs or summary.max_drawdown_r < other.max_drawdown_r))
    return Check("vs_long_only", value, "better on one", passed)
