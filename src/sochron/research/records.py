"""RunRecord, the registry line it encodes to, and the decoding and pairing checks of a registry file.

Canonical form (contract D12): json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
encoded as ASCII; Decimal as str() unchanged, datetime as %Y-%m-%dT%H:%M:%SZ, tuples as lists, nested
dataclasses as objects keyed by field name, None as null. run_id is the SHA-256 of the record without
the key run_id; a line is the whole record plus LF. Comparisons the contract makes "as record strings"
use plain(), the JSON values of the fields, so Decimal("1E+4") and Decimal("10000") differ.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sochron.costs import CostModel

from .model import (
    BASELINE_RUNS,
    PARAM_NAMES,
    PURPOSES,
    STATUSES,
    VARIANTS,
    BaselineSummary,
    Dataset,
    ResearchError,
    Summary,
    exact,
    exact_optional,
    finite,
    is_ascii,
    is_digits,
    is_hex,
    utc_text,
)

COST_FIELDS = tuple(item.name for item in fields(CostModel) if item.name != "provenance")
# Not part of a run's identity: what differs between a started line and its ok or failed line.
_NOT_IDENTITY = frozenset({"seq", "run_id", "status", "started_seq", "error", "summary", "baseline"})
# Fixed by the first started line of a hypothesis in a file (contract runner step 5, D16).
_SETUP = ("code_commit", "sizer_label", "equity", "rollover_zone", "rollover_at", "time_rule_server",
          "time_rule_version", "cost_provenance")
# Fields evaluate compares across records and the runner compares with the base (cost_model apart).
SHARED = ("dataset", "code_commit", "sizer_label", "equity", "rollover_zone", "rollover_at", "time_rule_server",
          "time_rule_version")


def _pairs(value: object, name: str) -> tuple[tuple[str, str], ...]:
    items = exact(value, tuple, name)
    for item in items:
        pair = exact(item, tuple, f"an item of {name}")
        if len(pair) != 2:
            raise ResearchError(f"an item of {name} must be a (name, value) pair")
        exact(pair[0], str, f"a name in {name}")
        exact(pair[1], str, f"a value in {name}")
    return items


def _names(pairs: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
    return tuple(name for name, _ in pairs)


def _rollover_at(text: str) -> bool:
    hours, colon, minutes = text.partition(":")
    return (colon == ":" and len(hours) == 2 and len(minutes) == 2 and is_digits(hours) and is_digits(minutes)
            and int(hours) < 24 and int(minutes) < 60)


@dataclass(frozen=True)
class RunRecord:
    """One registry line (contract "registry" field table); run_id is computed from the content."""

    seq: int
    status: str
    started_seq: int | None
    hypothesis: str
    purpose: str
    variant: str
    params: tuple[tuple[str, str], ...]
    base_run_id: str | None
    strategy_version: str
    backtest_version: str
    research_version: str
    code_commit: str
    dataset: Dataset
    cost_model: tuple[tuple[str, str], ...]
    cost_provenance: tuple[tuple[str, str], ...]
    equity: Decimal
    sizer_label: str
    rollover_zone: str
    rollover_at: str
    time_rule_server: str
    time_rule_version: str
    sides: tuple[str, ...]
    seed: int | None
    runs: int | None
    error: str | None
    summary: Summary | None
    baseline: BaselineSummary | None

    def __post_init__(self) -> None:
        self._check_types()
        self._check_values()

    def _check_types(self) -> None:
        exact(self.seq, int, "seq")
        for name in ("status", "hypothesis", "purpose", "variant", "strategy_version", "backtest_version",
                     "research_version", "code_commit", "sizer_label", "rollover_zone", "rollover_at",
                     "time_rule_server", "time_rule_version"):
            exact(getattr(self, name), str, name)
        for name in ("started_seq", "seed", "runs"):
            exact_optional(getattr(self, name), int, name)
        for name in ("base_run_id", "error"):
            exact_optional(getattr(self, name), str, name)
        for name in ("params", "cost_model", "cost_provenance"):
            _pairs(getattr(self, name), name)
        exact(self.dataset, Dataset, "dataset")
        exact(self.equity, Decimal, "equity")
        for side in exact(self.sides, tuple, "sides"):
            exact(side, str, "a side")
        exact_optional(self.summary, Summary, "summary")
        exact_optional(self.baseline, BaselineSummary, "baseline")

    def _check_values(self) -> None:
        if self.status not in STATUSES:
            raise ResearchError(f"status must be one of {STATUSES}")
        if self.purpose not in PURPOSES:
            raise ResearchError(f"purpose must be one of {PURPOSES}")
        if self.variant not in VARIANTS:
            raise ResearchError("variant must be 'A', 'B' or 'C'")
        if self.seq < 1:
            raise ResearchError("seq must be at least 1")
        if self.status == "started":
            if self.started_seq is not None:
                raise ResearchError("a started line has no started_seq")
        elif self.started_seq is None or not 1 <= self.started_seq < self.seq:
            raise ResearchError("an ok or failed line needs a started_seq from 1 to seq - 1")
        if not self.hypothesis or not is_ascii(self.hypothesis):
            raise ResearchError("hypothesis must be non-empty ASCII")
        if not is_hex(self.code_commit, 40):
            raise ResearchError("code_commit must be 40 lower-case hex characters")
        if self.purpose == "select":
            if self.base_run_id is not None:
                raise ResearchError("a select record has no base_run_id")
        elif self.base_run_id is None or not is_hex(self.base_run_id, 64):
            raise ResearchError("base_run_id must be 64 lower-case hex characters for every purpose but select")
        if _names(self.params) != PARAM_NAMES:
            raise ResearchError(f"params must be named {PARAM_NAMES} in that order")
        if _names(self.cost_model) != COST_FIELDS:
            raise ResearchError(f"cost_model must be named {COST_FIELDS} in that order")
        provenance = _names(self.cost_provenance)
        if any(first >= second for first, second in zip(provenance, provenance[1:])):
            raise ResearchError("cost_provenance must be sorted by name, each name once")
        finite(self.equity, "equity")
        if self.equity <= 0:
            raise ResearchError("equity must be positive")
        if not self.sizer_label or not is_ascii(self.sizer_label):
            raise ResearchError("sizer_label must be non-empty ASCII")
        if not _rollover_at(self.rollover_at):
            raise ResearchError("rollover_at must be HH:MM")
        if self.sides != (("long",) if self.purpose == "long_only" else ("long", "short")):
            raise ResearchError("sides must be ['long'] for long_only and ['long', 'short'] otherwise")
        self._check_by_status()

    def _check_by_status(self) -> None:
        if self.purpose == "random_entry":
            base = self.base_run_id or ""
            if self.runs != BASELINE_RUNS or self.seed != int(base[:15], 16):
                raise ResearchError("a random_entry record has runs 1000 and seed int(base_run_id[:15], 16)")
        elif self.seed is not None or self.runs is not None:
            raise ResearchError("only a random_entry record has seed and runs")
        if (self.status == "failed") != (self.error is not None):
            raise ResearchError("error is set on a failed line only")
        if self.error is not None and not is_ascii(self.error):
            raise ResearchError("error must be ASCII")
        ok = self.status == "ok"
        if (self.summary is not None) != (ok and self.purpose != "random_entry"):
            raise ResearchError("summary is set on an ok line of every purpose but random_entry only")
        if (self.baseline is not None) != (ok and self.purpose == "random_entry"):
            raise ResearchError("baseline is set on an ok line of random_entry only")

    @property
    def run_id(self) -> str:
        return hashlib.sha256(canonical(plain(self))).hexdigest()

    def line(self) -> bytes:
        obj = plain(self)
        obj["run_id"] = hashlib.sha256(canonical(obj)).hexdigest()
        return canonical(obj) + b"\n"


RECORD_FIELDS = tuple(item.name for item in fields(RunRecord))


def _json(value: object) -> Any:
    if value is None or type(value) in (str, int, bool):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return utc_text(value)
    if isinstance(value, tuple):
        return [_json(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _json(getattr(value, item.name)) for item in fields(value)}
    raise TypeError(f"no registry form for {type(value).__name__}")


def plain(record: RunRecord) -> dict[str, Any]:
    """The JSON values of every field (the record strings), without run_id."""
    return {name: _json(getattr(record, name)) for name in RECORD_FIELDS}


def canonical(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def identity(record: RunRecord) -> bytes:
    """Every field but seq, run_id, status, started_seq, error, summary and baseline (F35)."""
    obj = plain(record)
    return canonical({name: value for name, value in obj.items() if name not in _NOT_IDENTITY})


def record_string(record: RunRecord, name: str) -> bytes:
    """One field as the registry writes it (a key for counting distinct values)."""
    return canonical({name: plain(record)[name]})


def costs_but_stress(record: RunRecord) -> tuple[tuple[str, str], ...]:
    return tuple(pair for pair in record.cost_model if pair[0] != "stress_factor")


def stress_factor(record: RunRecord) -> str:
    return dict(record.cost_model)["stress_factor"]


def setup(record: RunRecord) -> bytes:
    """What the first started line of a hypothesis fixes for the file (F33)."""
    obj = plain(record)
    fixed = {name: obj[name] for name in _SETUP}
    fixed["cost_model"] = [list(pair) for pair in costs_but_stress(record)]
    return canonical(fixed)


# ---------------------------------------------------------------------------------- decoding


def _decimal_text(value: object, name: str) -> Decimal:
    """A Decimal from the text str() writes for a finite Decimal: -?D+(.D+)?(E[+-]D+)?"""
    if type(value) is not str:
        raise ResearchError(f"{name} must be a decimal string")
    body = value[1:] if value.startswith("-") else value
    mantissa, marker, exponent = body.partition("E")
    whole, dot, fraction = mantissa.partition(".")
    valid = is_digits(whole) and (not dot or is_digits(fraction))
    if marker:
        valid = valid and exponent[:1] in ("+", "-") and is_digits(exponent[1:])
    if not valid:
        raise ResearchError(f"{name} is not a decimal number: {value!r}")
    try:
        return Decimal(value)
    except ArithmeticError:  # an exponent beyond what Decimal can hold
        raise ResearchError(f"{name} is outside the Decimal range: {value!r}") from None


def _optional_decimal(value: object, name: str) -> Decimal | None:
    return None if value is None else _decimal_text(value, name)


def _utc_text(value: object, name: str) -> datetime:
    if type(value) is not str or len(value) != 20 or value[4] + value[7] + value[10] + value[13] + value[16] + value[19] != "--T::Z":
        raise ResearchError(f"{name} must be written %Y-%m-%dT%H:%M:%SZ")
    parts = (value[0:4], value[5:7], value[8:10], value[11:13], value[14:16], value[17:19])
    if not all(is_digits(part) for part in parts):
        raise ResearchError(f"{name} must be written %Y-%m-%dT%H:%M:%SZ")
    year, month, day, hour, minute, second = (int(part) for part in parts)
    return datetime(year, month, day, hour, minute, second, tzinfo=UTC)


def _object(value: object, names: Sequence[str], name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise ResearchError(f"{name} must be an object")
    if set(value) != set(names):
        raise ResearchError(f"{name} must have exactly the keys {sorted(names)}")
    return value


def _json_pairs(value: object, name: str) -> tuple[tuple[str, str], ...]:
    if type(value) is not list:
        raise ResearchError(f"{name} must be a list")
    out = []
    for item in value:
        if type(item) is not list or len(item) != 2:
            raise ResearchError(f"an item of {name} must be a pair")
        out.append((item[0], item[1]))
    return tuple(out)


def _dataset(value: object) -> Dataset:
    obj = _object(value, [item.name for item in fields(Dataset)], "dataset")
    return Dataset(snapshot_id=obj["snapshot_id"], manifest_sha256=obj["manifest_sha256"],
                   period_start_utc=_utc_text(obj["period_start_utc"], "period_start_utc"),
                   period_end_utc=_utc_text(obj["period_end_utc"], "period_end_utc"), m1_bars=obj["m1_bars"])


def _summary(value: object) -> Summary | None:
    if value is None:
        return None
    obj = _object(value, [item.name for item in fields(Summary)], "summary")
    values = dict(obj)
    for name in ("max_drawdown_r", "net_money"):
        values[name] = _decimal_text(obj[name], name)
    for name in ("expectancy_r", "long_expectancy_r", "short_expectancy_r", "top5_removed_expectancy_r"):
        values[name] = _optional_decimal(obj[name], name)
    years = obj["expectancy_by_year"]
    if type(years) is not list or any(type(item) is not list or len(item) != 2 for item in years):
        raise ResearchError("expectancy_by_year must be a list of [year, expectancy] pairs")
    values["expectancy_by_year"] = tuple((item[0], _decimal_text(item[1], "a year's expectancy")) for item in years)
    return Summary(**values)


def _baseline(value: object) -> BaselineSummary | None:
    if value is None:
        return None
    obj = _object(value, [item.name for item in fields(BaselineSummary)], "baseline")
    values = dict(obj)
    for name in ("mean_r", "p05_r", "p50_r", "p95_r", "variant_mean_hold_m1", "baseline_mean_hold_m1"):
        values[name] = _decimal_text(obj[name], name)
    return BaselineSummary(**values)


def decode(line: bytes) -> RunRecord:
    """The record of one registry line (without its LF); ResearchError when it is not a canonical line."""
    if b"\r" in line:
        raise ResearchError("the line holds a carriage return")
    if any(byte > 127 for byte in line):
        raise ResearchError("the line holds a byte that is not ASCII")
    try:
        obj = json.loads(line.decode("ascii"))
    except ValueError as error:
        raise ResearchError(f"the line is not JSON ({error})") from None
    obj = _object(obj, RECORD_FIELDS + ("run_id",), "the record")
    values = dict(obj)
    del values["run_id"]
    for name in ("params", "cost_model", "cost_provenance"):
        values[name] = _json_pairs(obj[name], name)
    sides = obj["sides"]
    if type(sides) is not list:
        raise ResearchError("sides must be a list")
    values["sides"] = tuple(sides)
    values["equity"] = _decimal_text(obj["equity"], "equity")
    try:
        values["dataset"] = _dataset(obj["dataset"])
        values["summary"] = _summary(obj["summary"])
        values["baseline"] = _baseline(obj["baseline"])
        record = RunRecord(**values)
    except (TypeError, ValueError) as error:  # a wrong JSON type or value inside the line
        raise ResearchError(f"the record is not valid ({error})") from None
    if obj["run_id"] != record.run_id:
        raise ResearchError("run_id does not match the record's content")
    if record.line() != line + b"\n":
        raise ResearchError("the line is not in canonical form")
    return record


def check_pairing(records: Sequence[RunRecord], answered: set[int], record: RunRecord) -> None:
    """An ok or failed record names a started line of the same identity that has no result yet."""
    if record.status == "started":
        return
    started_seq = record.started_seq or 0
    if not 1 <= started_seq <= len(records):
        raise ResearchError(f"started_seq {started_seq} is not a line of the registry")
    target = records[started_seq - 1]
    if target.status != "started":
        raise ResearchError(f"started_seq {started_seq} is a {target.status} line, not a started line")
    if identity(target) != identity(record):
        raise ResearchError(f"the run differs from the started line {started_seq}")
    if started_seq in answered:
        raise ResearchError(f"the started line {started_seq} already has its result")


def parse(data: bytes) -> tuple[RunRecord, ...]:
    """Every record of a registry file's bytes; ResearchError names the torn byte offset or the bad line."""
    if not data:
        return ()
    if not data.endswith(b"\n"):
        offset = data.rfind(b"\n") + 1
        raise ResearchError(f"the registry ends with a torn line at byte offset {offset}")
    records: list[RunRecord] = []
    answered: set[int] = set()
    for number, line in enumerate(data[:-1].split(b"\n"), start=1):
        try:
            record = decode(line)
            if record.seq != number:
                raise ResearchError(f"seq {record.seq} where {number} is due")
            check_pairing(records, answered, record)
        except ResearchError as error:
            raise ResearchError(f"registry line {number}: {error}") from None
        if record.started_seq is not None:
            answered.add(record.started_seq)
        records.append(record)
    return tuple(records)
