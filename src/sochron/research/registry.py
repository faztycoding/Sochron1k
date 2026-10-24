"""The registry file: the only reads and writes of sochron.research (contract D12).

append_record checks the whole file and the new record, then writes the line with one write on a binary
append handle and flushes it. read_records reads bytes and refuses any line that is not canonical. No
code here rewrites, truncates or deletes a file. Runners write through this module's append_record looked
up at call time (the F39 seam). One runner process writes a file at a time (F42); nothing locks it.
"""

from pathlib import Path

from .model import ResearchError, exact
from .records import RunRecord, check_pairing, parse


def _path(path: object) -> Path:
    if not isinstance(path, Path):
        raise TypeError(f"the registry path must be a pathlib.Path, not {type(path).__name__}")
    return path


def read_records(path: Path) -> tuple[RunRecord, ...]:
    """Every record of the file; a file that does not exist yet has none. File system errors pass through."""
    try:
        data = _path(path).read_bytes()
    except FileNotFoundError:
        return ()
    return parse(data)


def append_record(path: Path, record: RunRecord) -> None:
    """Append record as the next line; ResearchError leaves the file as it was."""
    path = _path(path)
    exact(record, RunRecord, "record")
    if not path.name.endswith(".jsonl"):
        raise ResearchError("the registry path must end with .jsonl")
    records = read_records(path)
    if record.seq != len(records) + 1:
        raise ResearchError(f"seq {record.seq} where {len(records) + 1} is due")
    answered = {item.started_seq for item in records if item.started_seq is not None}
    check_pairing(records, answered, record)
    line = record.line()
    with open(path, "ab") as handle:
        handle.write(line)
        handle.flush()
