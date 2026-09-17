"""One bounded sync step. Real HTTP/config/scheduling are separate boundaries."""

from __future__ import annotations

import json
from typing import Protocol

from .native_source import ExportBatch
from .sync_journal import JournalUnavailable, Pending, SyncJournal, canonical


class DestinationUnavailable(RuntimeError):
    """Transport did not establish a trustworthy result; retain UNKNOWN."""


class DestinationConflict(RuntimeError):
    """Receiver confirmed a conflict; quarantine instead of replacing evidence."""


class SendBudgetExhausted(RuntimeError):
    def __init__(self) -> None:
        super().__init__("SYNC_SEND_BUDGET_EXHAUSTED")


class Destination(Protocol):
    owner_id: str
    origin: str

    def store(self, batch: ExportBatch) -> None: ...

    def read(self, batch: ExportBatch) -> object: ...


class SyncDriver:
    def __init__(
        self, journal: SyncJournal, destination: Destination, *, max_sends: int = 5
    ) -> None:
        if type(max_sends) is not int or not 1 <= max_sends <= 5:
            raise ValueError("invalid send budget")
        self.journal, self.destination = journal, destination
        self.max_sends = max_sends
        self._lock = journal.step_lock

    def _target(self) -> None:
        pinned = json.loads(self.journal.binding)
        source = self.journal.source
        if (
            self.destination.owner_id != pinned["owner_id"]
            or self.destination.origin != pinned["destination"]
            or str(source.directory) != pinned["source_directory"]
            or source.archive_id != pinned["archive_id"]
            or source.binding_json != pinned["binding_json"]
        ):
            raise JournalUnavailable()

    def _reconcile(self, pending: Pending) -> str:
        self._target()
        try:
            snapshot = self.destination.read(pending.batch)
        except DestinationUnavailable:
            return "UNKNOWN"
        except DestinationConflict:
            return self.journal.quarantine(pending.batch_id).state
        return self.journal.reconcile(pending.batch_id, snapshot).state

    def _source_matches(self, pending: Pending) -> bool:
        current = self.journal.source.read(pending.batch.after, limit=len(pending.batch.rows))
        return current.next_cursor == pending.batch.next_cursor and canonical(
            [json.loads(r.payload) for r in current.rows]
        ) == canonical([json.loads(r.payload) for r in pending.batch.rows])

    def reconcile_pending(self) -> str:
        """One pending read-back only; never prepare, send, or release quarantine."""
        if not self._lock.acquire(blocking=False):
            raise JournalUnavailable()
        try:
            self._target()
            pending = self.journal.status().pending
            if pending is None:
                return "NO_PENDING"
            if pending.state == "QUARANTINED":
                return pending.state
            if not self._source_matches(pending):
                return self.journal.quarantine(pending.batch_id).state
            if pending.state == "PREPARED":
                # A read must not manufacture an attempt to satisfy VERIFIED's invariant.
                return "REVIEW_REQUIRED"
            return self._reconcile(pending)
        finally:
            self._lock.release()

    def step(self) -> str:
        if not self._lock.acquire(blocking=False):
            raise JournalUnavailable()
        try:
            self._target()
            state = self.journal.status()
            pending = state.pending
            if pending is None:
                batch = self.journal.source.read(state.cursor)
                if not batch.rows:
                    return "IDLE"
                pending = self.journal.prepare(batch)
            if pending.state == "QUARANTINED":
                return pending.state
            # Validate current source before any external effect, including after restart.
            if not self._source_matches(pending):
                return self.journal.quarantine(pending.batch_id).state
            if pending.state == "UNKNOWN":
                # Missing rows become PREPARED but do not send again in this same step.
                return self._reconcile(pending)
            if pending.attempts >= self.max_sends:
                raise SendBudgetExhausted()
            pending = self.journal.begin_send(pending.batch_id)
            self._target()
            try:
                self.destination.store(pending.batch)
            except DestinationUnavailable:
                return "UNKNOWN"
            except DestinationConflict:
                return self.journal.quarantine(pending.batch_id).state
            # Even a successful store response is not acknowledgement evidence.
            return self._reconcile(pending)
        finally:
            self._lock.release()
