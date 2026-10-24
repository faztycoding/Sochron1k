"""run_variant(): one backtest.run recorded in the registry, inside the H001 budgets (contract "runner").

Steps 1-5 check everything and write nothing; step 6 appends the started line, step 7 runs the
backtest, step 8 appends the ok line, or after any exception the failed line, then raises the same
exception object. Lines go through registry.append_record looked up at call time (the F39 seam).
"""

from collections.abc import Sequence
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from sochron import backtest
from sochron.backtest import Result, Rollover, Side, Sizer
from sochron.core import Bar
from sochron.costs import CostModel
from sochron.strategy import H001Params
from sochron.timebase import TimeRule

from . import registry as registry_module  # the argument `registry` is the file path
from .inputs import (
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
from .model import Dataset, ResearchError, exact, exact_optional
from .records import RunRecord
from .stats import summarize

_RUN_PURPOSES = ("select", "robustness", "stress", "long_only")


def run_variant(
    m1: Sequence[Bar],
    m15: Sequence[object],
    params: H001Params,
    model: CostModel,
    sizer: Sizer,
    equity: Decimal,
    rule: TimeRule,
    rollover: Rollover,
    *,
    purpose: str,
    dataset: Dataset,
    code_commit: str,
    sizer_label: str,
    registry: Path,
    base_run_id: str | None = None,
) -> tuple[RunRecord, Result]:
    """Run one variant through backtest.run and record it; returns the ok record and the result."""
    path = registry
    holdout_guard(m1, m15, dataset)
    bars, bars15 = check_types(m1, m15, params, model, sizer, equity, rule, rollover, dataset, code_commit,
                               sizer_label, path)
    exact(purpose, str, "purpose")
    exact_optional(base_run_id, str, "base_run_id")
    if purpose not in _RUN_PURPOSES:
        raise ResearchError(f"run_variant runs the purposes {_RUN_PURPOSES}, not {purpose!r}")
    check_values(model, equity, code_commit, sizer_label, path, "2" if purpose == "stress" else "1")
    check_dataset(dataset, bars)
    check_bars(bars, bars15, rule)
    records = registry_module.read_records(path)
    started = started_record(seq=len(records) + 1, purpose=purpose, params=params, base_run_id=base_run_id,
                             model=model, equity=equity, rule=rule, rollover=rollover, dataset=dataset,
                             code_commit=code_commit, sizer_label=sizer_label)
    if base_run_id is not None:
        check_against_base(started, find_base(records, base_run_id, params.variant))
    check_budget(records, started)
    sides: frozenset[Side] = frozenset({"long"}) if purpose == "long_only" else frozenset({"long", "short"})
    registry_module.append_record(path, started)
    try:
        result = backtest.run(m1, m15, params, model, sizer, equity, rule, rollover, sides=sides)
        ok = replace(started, seq=started.seq + 1, status="ok", started_seq=started.seq,
                     summary=summarize(result, rule))
        registry_module.append_record(path, ok)
    except BaseException as error:  # KeyboardInterrupt and disk errors included (F39)
        record_failure(path, started, error)
        raise
    return ok, result
