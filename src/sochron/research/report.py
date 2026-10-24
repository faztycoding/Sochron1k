"""render_report(): the owner's Markdown report in Thai, line for line as the contract's template (F12, F22, F38).

Every part reads only the records whose hypothesis is the argument (F47). An Evaluation must sit on an
ok select record of its variant and, once a non-select line has fixed the variant's base, on that base
(F45). The text is returned, never written.
"""

from collections.abc import Mapping, Sequence

from .evaluate import Evaluation
from .model import (
    PURPOSES,
    ROBUSTNESS_BUDGET,
    SELECT_BUDGET,
    TOTAL_BUDGET,
    VARIANTS,
    ResearchError,
    exact,
    text,
    utc_text,
)
from .records import RunRecord, record_string

_SCREEN = "การประเมินนี้เป็น screen ไม่ใช่คำตัดสินของ H001: มีข้อมูลก่อน cutoff ของ holdout"
_OWNER = (
    "## สิ่งที่เจ้าของตัดสินเอง",
    "",
    "- holdout ครอบคลุม regime เดียวหรือไม่",
    "- leakage audit",
    "- วิธีรวมคำตัดสินของหลายโครงสร้าง: ทดสอบหลายโครงสร้างทำให้โอกาสได้ go โดยบังเอิญสูงขึ้น",
)
_NOT_COUNTED = "ไม่นับ"


def _started(records: Sequence[RunRecord], variant: str, purpose: str) -> list[RunRecord]:
    return [item for item in records if item.variant == variant and item.purpose == purpose
            and item.status == "started"]


def _registry_rows(records: Sequence[RunRecord]) -> tuple[list[str], int]:
    """The 15 rows of the registry table and the number of runs counted against the 63."""
    answered = {item.started_seq for item in records if item.started_seq is not None}
    rows = []
    counted = 0
    for variant in VARIANTS:
        for purpose in PURPOSES:
            group = [item for item in records if item.variant == variant and item.purpose == purpose]
            started = [item for item in group if item.status == "started"]
            ok = sum(1 for item in group if item.status == "ok")
            failed = sum(1 for item in group if item.status == "failed")
            interrupted = sum(1 for item in started if item.seq not in answered)
            if purpose == "select":
                distinct = len({item.params for item in started})
                budget = f"{distinct}/{SELECT_BUDGET}"
                counted += distinct
            elif purpose == "robustness":
                budget = f"{len(started)}/{ROBUSTNESS_BUDGET}"
                counted += len(started)
            elif purpose == "stress":
                budget = f"{ok}/1"
                counted += len(started)
            else:
                budget = _NOT_COUNTED
            rows.append(f"| {variant} | {purpose} | {len(started)} | {ok} | {failed} | {interrupted} | {budget} |")
    return rows, counted


def _base(records: Sequence[RunRecord], key: str, evaluation: Evaluation) -> RunRecord:
    """The select ok record the Evaluation sits on; it must be the variant's locked base once there is one."""
    if key not in VARIANTS or key != evaluation.variant:
        raise ResearchError(f"the key {key!r} must be the Evaluation's variant, one of {VARIANTS}")
    base = next((item for item in records if item.status == "ok" and item.purpose == "select"
                 and item.variant == key and item.run_id == evaluation.base_run_id), None)
    if base is None:
        raise ResearchError(f"the Evaluation of {key} is not on an ok select record of {key} in these records")
    locked = next((item.base_run_id for item in records
                   if item.status == "started" and item.purpose != "select" and item.variant == key), None)
    if locked is not None and locked != evaluation.base_run_id:
        raise ResearchError(f"the Evaluation of {key} is not on the variant's locked base {locked}")
    return base


def _section(records: Sequence[RunRecord], evaluation: Evaluation, base: RunRecord) -> list[str]:
    variant = evaluation.variant
    dataset = evaluation.dataset
    costs = ";".join(f"{name}={value}" for name, value in base.cost_model)
    datasets = len({record_string(item, "dataset") for item in _started(records, variant, "select")})
    lines = [
        f"## ผลการประเมิน {variant}",
        "",
        f"ชุดข้อมูล: {dataset.snapshot_id} {utc_text(dataset.period_start_utc)} ถึง {utc_text(dataset.period_end_utc)}",
        f"setup: commit {base.code_commit} · sizer {base.sizer_label} · equity {text(base.equity)} · rollover "
        f"{base.rollover_zone} {base.rollover_at} · กฎเวลา {base.time_rule_server} {base.time_rule_version} · "
        f"cost_model {costs}",
        f"ชุดข้อมูลที่ select ของ {variant} ใช้: {datasets}",
    ]
    if evaluation.screen:
        lines.append(_SCREEN)
    lines += ["", "| # | เงื่อนไข | ค่า | เกณฑ์ | ผล |", "|---|---|---|---|---|"]
    for number, check in enumerate(evaluation.checks, start=1):
        result = "ผ่าน" if check.passed else "ไม่ผ่าน"
        lines.append(f"| {number} | {check.name} | {check.value} | {check.threshold} | {result} |")
    lines += ["", f"คำตัดสิน: {evaluation.verdict}", ""]
    return lines


def _limits(records: Sequence[RunRecord]) -> list[str]:
    lines = ["## ข้อจำกัดที่ต้องรายงาน", "", "- drawdown วัดจาก realized curve เท่านั้น"]
    for item in records:
        summary = item.summary
        if item.status == "ok" and summary is not None:
            lines.append(f"- {item.variant} {item.purpose} seq {item.seq}: ambiguous {summary.ambiguous_trades}, "
                         f"data flag {summary.flagged_trades}, fill หลังข้อมูลขาด {summary.gap_fills}, "
                         f"ข้อมูลหมด {summary.end_of_data_trades}")
    for item in records:
        baseline = item.baseline
        if item.status == "ok" and baseline is not None:
            lines.append(f"- baseline {item.variant} seq {item.seq}: runs {baseline.runs}, seed {baseline.seed}, "
                         f"mean {text(baseline.mean_r)}, P5 {text(baseline.p05_r)}, P50 {text(baseline.p50_r)}, "
                         f"P95 {text(baseline.p95_r)}, ระยะถือ M1 variant {text(baseline.variant_mean_hold_m1)}/"
                         f"{baseline.variant_median_hold_m1}, baseline {text(baseline.baseline_mean_hold_m1)}/"
                         f"{baseline.baseline_median_hold_m1}")
    return lines + [""]


def render_report(records: Sequence[RunRecord], evaluations: Mapping[str, Evaluation], *,
                  hypothesis: str = "H001") -> str:
    """The report of hypothesis from the registry records and the Evaluations keyed by variant."""
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise TypeError(f"records must be a sequence of RunRecord, not {type(records).__name__}")
    for index, item in enumerate(records):
        exact(item, RunRecord, f"records[{index}]")
    if not isinstance(evaluations, Mapping):
        raise TypeError(f"evaluations must be a mapping of variant to Evaluation, not {type(evaluations).__name__}")
    for value in evaluations.values():
        exact(value, Evaluation, "an evaluation")
    exact(hypothesis, str, "hypothesis")
    own = sorted((item for item in records if item.hypothesis == hypothesis), key=lambda item: item.seq)
    bases = {key: _base(own, key, evaluation) for key, evaluation in evaluations.items()}
    rows, counted = _registry_rows(own)
    lines = [f"# รายงานวิจัย {hypothesis}", "", "## Registry", "",
             "| โครงสร้าง | purpose | started | ok | failed | interrupted | งบ |", "|---|---|---|---|---|---|---|",
             *rows, "", f"รวมที่นับงบ: {counted}/{TOTAL_BUDGET}", ""]
    for variant in VARIANTS:
        if variant in evaluations:
            lines += _section(own, evaluations[variant], bases[variant])
    lines += _limits(own) + list(_OWNER)
    return "\n".join(lines) + "\n"
