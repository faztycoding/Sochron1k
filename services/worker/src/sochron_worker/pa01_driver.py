"""One bounded PA01 publication step; UNKNOWN always reconciles before retry."""

from __future__ import annotations

import json
from typing import Protocol

from .pa01_envelope import PA01DecisionEnvelope
from .pa01_journal import PA01JournalUnavailable, PA01Pending, PA01ProducerJournal


class PA01DestinationUnavailable(RuntimeError):
    """Transport did not establish a trustworthy result; retain UNKNOWN."""


class PA01DestinationConflict(RuntimeError):
    """Receiver confirmed incompatible evidence; quarantine it."""


class PA01SendBudgetExhausted(RuntimeError):
    def __init__(self) -> None:
        super().__init__("PA01_SEND_BUDGET_EXHAUSTED")


class PA01Destination(Protocol):
    owner_id: str
    strategy_version_id: int
    experiment_id: int
    origin: str

    def store(self, envelope: PA01DecisionEnvelope) -> None: ...

    def read(self, envelope: PA01DecisionEnvelope) -> object: ...


class PA01ProducerDriver:
    def __init__(
        self,
        journal: PA01ProducerJournal,
        destination: PA01Destination,
        *,
        max_sends: int = 5,
    ) -> None:
        if type(max_sends) is not int or not 1 <= max_sends <= 5:
            raise ValueError("invalid send budget")
        self.journal, self.destination = journal, destination
        self.max_sends = max_sends
        self._lock = journal.step_lock

    def _target(self) -> None:
        pinned = json.loads(self.journal.binding)
        source = self.journal.source
        archive = source.archive
        if (
            self.destination.owner_id != pinned["owner_id"]
            or self.destination.strategy_version_id != pinned["strategy_version_id"]
            or self.destination.experiment_id != pinned["experiment_id"]
            or self.destination.origin != pinned["destination"]
            or str(archive.directory) != pinned["source_directory"]
            or archive.archive_id != pinned["archive_id"]
            or json.loads(archive.binding_json) != pinned["archive_binding"]
            or str(source.policy.path) != pinned["policy_file"]
            or source.code_hash != pinned["code_hash"]
        ):
            raise PA01JournalUnavailable()

    def _reconcile(self, pending: PA01Pending) -> str:
        self._target()
        try:
            snapshot = self.destination.read(pending.envelope)
        except PA01DestinationUnavailable:
            return "UNKNOWN"
        except PA01DestinationConflict:
            return self.journal.quarantine(pending.signal_id).state
        return self.journal.reconcile(pending.signal_id, snapshot).state

    def reconcile_pending(self) -> str:
        """Read one UNKNOWN decision only; never prepare, send or release quarantine."""
        if not self._lock.acquire(blocking=False):
            raise PA01JournalUnavailable()
        try:
            self._target()
            pending = self.journal.status().pending
            if pending is None:
                return "NO_PENDING"
            if pending.state == "QUARANTINED":
                return pending.state
            if pending.state == "PREPARED":
                return "REVIEW_REQUIRED"
            return self._reconcile(pending)
        finally:
            self._lock.release()

    def step(self) -> str:
        if not self._lock.acquire(blocking=False):
            raise PA01JournalUnavailable()
        try:
            self._target()
            status = self.journal.status()
            pending = status.pending
            if pending is None:
                envelope = self.journal.source.next(status.last_formed_at)
                if envelope is None:
                    return "IDLE"
                pending = self.journal.prepare(envelope)
            if pending.state == "QUARANTINED":
                return pending.state
            if pending.state == "UNKNOWN":
                return self._reconcile(pending)
            if pending.attempts >= self.max_sends:
                raise PA01SendBudgetExhausted()
            pending = self.journal.begin_send(pending.signal_id)
            self._target()
            try:
                self.destination.store(pending.envelope)
            except PA01DestinationUnavailable:
                return "UNKNOWN"
            except PA01DestinationConflict:
                return self.journal.quarantine(pending.signal_id).state
            return self._reconcile(pending)
        finally:
            self._lock.release()
