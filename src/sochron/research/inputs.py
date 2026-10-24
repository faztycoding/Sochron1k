"""The checks run_variant and random_entry_baseline share before they write (contract runner steps 1-5,
baseline steps 1-2) and the failed line they write after an exception.

The M1/M15 checks repeat CORE-007 "Input และการตรวจ" with ResearchError, because backtest keeps its own
private (the one exception to "no rule written twice", F30): bad data is refused before any line, so it
never uses budget.
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import cast

from sochron.backtest import BACKTEST_VERSION, Rollover
from sochron.core import Bar
from sochron.costs import CostModel
from sochron.strategy import STRATEGY_VERSION, H001Params, StrategyError, Variant
from sochron.timebase import RAW_MAX_EXCLUSIVE, RAW_MIN, TimeRule, bar_open, to_utc

from . import registry
from .model import (
    BASELINE_RUNS,
    HOLDOUT_CUTOFF_UTC,
    HYPOTHESIS,
    PARAM_NAMES,
    RESEARCH_VERSION,
    ROBUSTNESS_BUDGET,
    SELECT_BUDGET,
    TOTAL_BUDGET,
    BudgetExceeded,
    Dataset,
    HoldoutRefused,
    ResearchError,
    ascii_text,
    exact,
    is_ascii,
    is_hex,
    utc_text,
)
from .records import COST_FIELDS, SHARED, RunRecord, costs_but_stress, identity, plain, setup
from .robustness import neighbours

M15 = list[tuple[Bar, frozenset[str]]]


def _items(value: object) -> Sequence[object]:
    """value when it is a sequence the guard may read, else nothing (a generator is left for the type check)."""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()


def _past_cutoff(value: object) -> bool:
    return isinstance(value, datetime) and value.utcoffset() is not None and value >= HOLDOUT_CUTOFF_UTC


def holdout_guard(m1: object, m15: object, dataset: object) -> None:
    """Step 1, before every other check: no bar from the cutoff on, no Dataset ending after it (D11)."""
    cutoff = utc_text(HOLDOUT_CUTOFF_UTC)
    for index, bar in enumerate(_items(m1)):
        if _past_cutoff(getattr(bar, "time_utc", None)):
            raise HoldoutRefused(f"m1[{index}] is at or after the holdout cutoff {cutoff}")
    for index, item in enumerate(_items(m15)):
        if _past_cutoff(getattr(getattr(item, "bar", None), "time_utc", None)):
            raise HoldoutRefused(f"m15[{index}] is at or after the holdout cutoff {cutoff}")
    if type(dataset) is Dataset and dataset.period_end_utc > HOLDOUT_CUTOFF_UTC:
        raise HoldoutRefused(f"the Dataset ends after the holdout cutoff {cutoff}")


def _sequence(value: object, name: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence, not {type(value).__name__}")
    return value


def check_types(m1: object, m15: object, params: object, model: object, sizer: object, equity: object,
                rule: object, rollover: object, dataset: object, code_commit: object, sizer_label: object,
                path: object) -> tuple[Sequence[Bar], M15]:
    """Every argument's type (TypeError); returns the M1 bars and the M15 (bar, flags) pairs."""
    bars = _sequence(m1, "m1")
    for index, bar in enumerate(bars):
        exact(bar, Bar, f"m1[{index}]")
    bars15: M15 = []
    for index, item in enumerate(_sequence(m15, "m15")):
        bar = exact(getattr(item, "bar", None), Bar, f"m15[{index}].bar")
        flags = exact(getattr(item, "flags", None), frozenset, f"m15[{index}].flags")
        for flag in flags:
            exact(flag, str, f"a flag of m15[{index}]")
        bars15.append((bar, flags))
    exact(params, H001Params, "params")
    exact(model, CostModel, "model")
    if not callable(sizer):
        raise TypeError("sizer must be callable")
    exact(equity, Decimal, "equity")
    exact(rule, TimeRule, "rule")
    exact(rollover, Rollover, "rollover")
    exact(dataset, Dataset, "dataset")
    exact(code_commit, str, "code_commit")
    exact(sizer_label, str, "sizer_label")
    if not isinstance(path, Path):
        raise TypeError(f"registry must be a pathlib.Path, not {type(path).__name__}")
    return cast(Sequence[Bar], bars), bars15


def check_values(model: CostModel, equity: Decimal, code_commit: str, sizer_label: str, path: Path,
                 stress_factor: str) -> None:
    """Scalar values: the stress factor as a record string (F19), commit, label, equity and the path."""
    if str(model.stress_factor) != stress_factor:
        raise ResearchError(f"this purpose needs a model with stress_factor {stress_factor!r}, "
                            f"not {str(model.stress_factor)!r}")
    if not is_hex(code_commit, 40):
        raise ResearchError("code_commit must be 40 lower-case hex characters")
    if not sizer_label or not is_ascii(sizer_label):
        raise ResearchError("sizer_label must be non-empty ASCII")
    if not equity.is_finite() or equity <= 0:
        raise ResearchError("equity must be finite and positive")
    if not path.name.endswith(".jsonl"):
        raise ResearchError("the registry path must end with .jsonl")


def _check_time(bar: Bar, rule: TimeRule, name: str) -> None:
    if not RAW_MIN <= bar.time_raw < RAW_MAX_EXCLUSIVE or bar.time_utc != to_utc(bar.time_raw, rule):
        raise ResearchError(f"{name} time_utc does not match its raw time under the rule")


def _check_m1(bar: Bar, previous: Bar | None, rule: TimeRule, name: str) -> None:
    if bar.timeframe != 1:
        raise ResearchError(f"{name} is not an M1 bar")
    if previous is not None and bar.time_raw <= previous.time_raw:
        raise ResearchError(f"{name} time is not after the M1 before it")
    if bar.spread is not None and bar.spread < 0:
        raise ResearchError(f"{name} has a negative spread")
    if min(bar.open, bar.high, bar.low, bar.close) <= 0:
        raise ResearchError(f"{name} has a price that is zero or negative")
    if bar.high < bar.low or not bar.low <= bar.open <= bar.high or not bar.low <= bar.close <= bar.high:
        raise ResearchError(f"{name} has inconsistent OHLC")
    _check_time(bar, rule, name)


def check_bars(m1: Sequence[Bar], bars15: M15, rule: TimeRule) -> tuple[list[int], list[int]]:
    """The CORE-007 input checks (ResearchError); returns the first M1 of every M15 bar and the bar of every M1."""
    if not m1 or not bars15:
        raise ResearchError("m1 and m15 must not be empty")
    previous = None
    for index, bar in enumerate(m1):
        _check_m1(bar, previous, rule, f"m1[{index}]")
        previous = bar
    for index, (bar, _) in enumerate(bars15):
        if bar.timeframe != 15:
            raise ResearchError(f"m15[{index}] is not an M15 bar")
        if index and bar.time_raw <= bars15[index - 1][0].time_raw:
            raise ResearchError(f"m15[{index}] time is not after the bar before it")
        _check_time(bar, rule, f"m15[{index}]")
    first = [0] * len(bars15)
    counts = [0] * len(bars15)
    bar_of = []
    current = 0
    for index, bar in enumerate(m1):
        opened = bar_open(bar.time_raw, 15, rule)
        while current < len(bars15) and bars15[current][0].time_raw < opened:
            if counts[current] == 0:
                raise ResearchError(f"m15[{current}] has no M1 bar")
            current += 1
        if current == len(bars15) or bars15[current][0].time_raw != opened:
            raise ResearchError(f"m1[{index}] is not inside any M15 bar")
        if counts[current] == 0:
            first[current] = index
        counts[current] += 1
        bar_of.append(current)
    if current != len(bars15) - 1:
        raise ResearchError(f"m15[{current + 1}] has no M1 bar")
    return first, bar_of


def check_dataset(dataset: Dataset, m1: Sequence[Bar]) -> None:
    """The Dataset counts every M1 and its period [start, end) holds every M1 time."""
    if dataset.m1_bars != len(m1):
        raise ResearchError(f"the Dataset counts {dataset.m1_bars} M1 bars, the input has {len(m1)}")
    for index, bar in enumerate(m1):
        if not dataset.period_start_utc <= bar.time_utc < dataset.period_end_utc:
            raise ResearchError(f"m1[{index}] is outside the Dataset period")


def param_pairs(params: H001Params) -> tuple[tuple[str, str], ...]:
    return tuple((name, str(getattr(params, name))) for name in PARAM_NAMES)


def params_of(record: RunRecord) -> H001Params:
    """The H001Params whose record strings are record.params; ResearchError when there are none."""
    values = dict(record.params)
    variant = cast(Variant, record.variant)  # RunRecord keeps variant to A, B or C
    try:
        params = H001Params(variant=variant, f=int(values["f"]), s=int(values["s"]), n=int(values["n"]),
                            theta=Decimal(values["theta"]), N=int(values["N"]), M=int(values["M"]),
                            k=Decimal(values["k"]))
    except (ArithmeticError, StrategyError, ValueError):
        raise ResearchError(f"record seq {record.seq} does not hold valid H001 params") from None
    if param_pairs(params) != record.params:
        raise ResearchError(f"record seq {record.seq} does not hold H001 params as their record strings")
    return params


def started_record(*, seq: int, purpose: str, params: H001Params, base_run_id: str | None, model: CostModel,
                   equity: Decimal, rule: TimeRule, rollover: Rollover, dataset: Dataset, code_commit: str,
                   sizer_label: str) -> RunRecord:
    """The started line of a run, every field as the registry table derives it from the inputs."""
    random_entry = purpose == "random_entry"
    return RunRecord(
        seq=seq, status="started", started_seq=None, hypothesis=HYPOTHESIS, purpose=purpose, variant=params.variant,
        params=param_pairs(params), base_run_id=base_run_id, strategy_version=STRATEGY_VERSION,
        backtest_version=BACKTEST_VERSION, research_version=RESEARCH_VERSION, code_commit=code_commit,
        dataset=dataset, cost_model=tuple((name, str(getattr(model, name))) for name in COST_FIELDS),
        cost_provenance=tuple(sorted((name, item.status) for name, item in model.provenance.items())),
        equity=equity, sizer_label=sizer_label, rollover_zone=rollover.zone,
        rollover_at=f"{rollover.at.hour:02d}:{rollover.at.minute:02d}", time_rule_server=rule.server,
        time_rule_version=rule.version, sides=("long",) if purpose == "long_only" else ("long", "short"),
        seed=int(base_run_id[:15], 16) if random_entry and base_run_id is not None else None,
        runs=BASELINE_RUNS if random_entry else None, error=None, summary=None, baseline=None,
    )


def find_base(records: Sequence[RunRecord], base_run_id: str, variant: str) -> RunRecord:
    """The ok select record of H001 and the variant that base_run_id names (step 4)."""
    base = next((record for record in records if record.run_id == base_run_id), None)
    if base is None:
        raise ResearchError("base_run_id names no record of the registry")
    if base.status != "ok" or base.purpose != "select" or base.hypothesis != HYPOTHESIS or base.variant != variant:
        raise ResearchError(f"the base (seq {base.seq}) must be an ok select record of {HYPOTHESIS}, variant {variant}")
    return base


def different_field(record: RunRecord, other: RunRecord) -> str | None:
    """The first field evaluate compares that differs as a record string (cost_model without stress_factor)."""
    mine, theirs = plain(record), plain(other)
    for name in SHARED:
        if mine[name] != theirs[name]:
            return name
    if costs_but_stress(record) != costs_but_stress(other):
        return "cost_model"
    return None


def check_against_base(record: RunRecord, base: RunRecord) -> None:
    """Step 4: the compared fields equal the base's; params a valid neighbour (robustness) or the base's."""
    name = different_field(record, base)
    if name is not None:
        raise ResearchError(f"{name} differs from the base (seq {base.seq})")
    if record.purpose == "robustness":
        valid = {param_pairs(item.params) for item in neighbours(params_of(base)) if item.params is not None}
        if record.params not in valid:
            raise ResearchError(f"params are not a valid neighbour of the base (seq {base.seq})")
    elif record.params != base.params:
        raise ResearchError(f"params differ from the base (seq {base.seq})")


def check_budget(records: Sequence[RunRecord], record: RunRecord) -> None:
    """Step 5, counted from the started lines of the record's hypothesis (BudgetExceeded)."""
    lines = [item for item in records if item.hypothesis == record.hypothesis]
    started = [item for item in lines if item.status == "started"]
    if started and setup(started[0]) != setup(record):
        raise BudgetExceeded(f"the setup differs from the first started line of {record.hypothesis} in this file "
                             f"(seq {started[0].seq}); a new setup needs a new registry file")
    if record.purpose != "select":
        locked = next((item.base_run_id for item in started
                       if item.purpose != "select" and item.variant == record.variant), None)
        if locked is not None and locked != record.base_run_id:
            raise BudgetExceeded(f"variant {record.variant} already has its base {locked}")
    run = identity(record)
    if any(item.status == "ok" and identity(item) == run for item in lines):
        raise BudgetExceeded("this run already has an ok line")
    selected: dict[str, set[tuple[tuple[str, str], ...]]] = {}
    robustness: dict[str, int] = {}
    stress = 0
    for item in started:
        if item.purpose == "select":
            selected.setdefault(item.variant, set()).add(item.params)
        elif item.purpose == "robustness":
            robustness[item.variant] = robustness.get(item.variant, 0) + 1
        elif item.purpose == "stress":
            stress += 1
    own = selected.get(record.variant, set())
    new_select = record.purpose == "select" and record.params not in own
    if new_select and len(own) >= SELECT_BUDGET:
        raise BudgetExceeded(f"variant {record.variant} already ran {SELECT_BUDGET} select params sets")
    if record.purpose == "robustness" and robustness.get(record.variant, 0) >= ROBUSTNESS_BUDGET:
        raise BudgetExceeded(f"variant {record.variant} already has {ROBUSTNESS_BUDGET} robustness started lines")
    counted = sum(len(item) for item in selected.values()) + sum(robustness.values()) + stress
    if counted + (1 if new_select or record.purpose in ("robustness", "stress") else 0) > TOTAL_BUDGET:
        raise BudgetExceeded(f"{record.hypothesis} already counts {counted} of its {TOTAL_BUDGET} runs")


def record_failure(path: Path, started: RunRecord, error: BaseException) -> None:
    """Try to append the failed line of started; when that fails too, the caller raises its first error."""
    try:
        failed = replace(started, seq=started.seq + 1, status="failed", started_seq=started.seq,
                         error=ascii_text(f"{type(error).__name__}: {error}"))
        registry.append_record(path, failed)
    except BaseException:  # runner step 8: the started line stays as an interrupted run
        return
