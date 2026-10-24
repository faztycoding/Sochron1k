"""The H001 research loop as pure functions plus one registry file (docs/contracts/CORE-008-research.md).

run_variant() records every backtest.run in an append-only JSONL registry inside the budgets of H001
section 4; random_entry_baseline() draws the H001 section 7 baseline with a seed taken from the base
record; neighbours() builds the robustness sets; evaluate() checks the H001 section 8 conditions; and
render_report() writes the owner's report. No clock, no float, randomness only from a seeded
random.Random, and file I/O only in sochron.research.registry.
"""

from .baseline import BaselineResult, random_entry_baseline
from .evaluate import Check, Evaluation, evaluate
from .model import (
    BASELINE_RUNS,
    HOLDOUT_CUTOFF_UTC,
    RESEARCH_VERSION,
    USED_PARAMETERS,
    BaselineSummary,
    BudgetExceeded,
    Dataset,
    HoldoutRefused,
    Purpose,
    ResearchError,
    Summary,
)
from .records import RunRecord
from .registry import append_record, read_records
from .report import render_report
from .robustness import Neighbour, neighbours
from .runner import run_variant
from .stats import percentile, summarize

__all__ = [
    "BASELINE_RUNS",
    "BaselineResult",
    "BaselineSummary",
    "BudgetExceeded",
    "Check",
    "Dataset",
    "Evaluation",
    "HOLDOUT_CUTOFF_UTC",
    "HoldoutRefused",
    "Neighbour",
    "Purpose",
    "RESEARCH_VERSION",
    "ResearchError",
    "RunRecord",
    "Summary",
    "USED_PARAMETERS",
    "append_record",
    "evaluate",
    "neighbours",
    "percentile",
    "random_entry_baseline",
    "read_records",
    "render_report",
    "run_variant",
    "summarize",
]
