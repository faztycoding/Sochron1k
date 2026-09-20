"""One bounded research-evaluation publication step with read-back reconciliation."""

from __future__ import annotations

import json
from typing import Protocol

from .research_evaluation import ResearchEvaluationEnvelope
from .research_evaluation_journal import (
    ResearchEvaluationJournal,
    ResearchEvaluationJournalUnavailable,
)


class ResearchEvaluationDestinationUnavailable(RuntimeError):
    pass


class ResearchEvaluationDestinationConflict(RuntimeError):
    pass


class ResearchEvaluationSendBudgetExhausted(RuntimeError):
    def __init__(self) -> None:
        super().__init__("RESEARCH_EVALUATION_SEND_BUDGET_EXHAUSTED")


class ResearchEvaluationDestination(Protocol):
    owner_id: str
    strategy_version_id: int
    experiment_id: int | None
    origin: str

    def store(self, envelope: ResearchEvaluationEnvelope) -> None: ...

    def read(self, envelope: ResearchEvaluationEnvelope) -> object: ...


class ResearchEvaluationDriver:
    def __init__(
        self,
        journal: ResearchEvaluationJournal,
        destination: ResearchEvaluationDestination,
        *,
        max_sends: int = 3,
    ) -> None:
        if type(max_sends) is not int or not 1 <= max_sends <= 3:
            raise ValueError("invalid send budget")
        self.journal = journal
        self.destination = destination
        self.max_sends = max_sends
        self._lock = journal.step_lock

    def _target(self) -> None:
        pinned = json.loads(self.journal.binding)
        if (
            self.destination.owner_id != pinned["owner_id"]
            or self.destination.strategy_version_id != pinned["strategy_version_id"]
            or self.destination.experiment_id != pinned["experiment_id"]
            or self.destination.origin != pinned["destination"]
            or str(self.journal.input_file) != pinned["input_file"]
            or self.journal.envelope.dataset_hash != pinned["dataset_hash"]
            or self.journal.envelope.evaluation_fingerprint
            != pinned["evaluation_fingerprint"]
        ):
            raise ResearchEvaluationJournalUnavailable()

    def _reconcile(self) -> str:
        self._target()
        pending = self.journal.status().pending
        try:
            snapshot = self.destination.read(pending.envelope)
        except ResearchEvaluationDestinationUnavailable:
            return "UNKNOWN"
        except ResearchEvaluationDestinationConflict:
            return self.journal.quarantine(pending.fingerprint).state
        return self.journal.reconcile(pending.fingerprint, snapshot).state

    def reconcile_pending(self) -> str:
        if not self._lock.acquire(blocking=False):
            raise ResearchEvaluationJournalUnavailable()
        try:
            self._target()
            pending = self.journal.status().pending
            if pending.state == "UNKNOWN":
                return self._reconcile()
            if pending.state == "PREPARED":
                return "REVIEW_REQUIRED"
            return pending.state
        finally:
            self._lock.release()

    def step(self) -> str:
        if not self._lock.acquire(blocking=False):
            raise ResearchEvaluationJournalUnavailable()
        try:
            self._target()
            pending = self.journal.status().pending
            if pending.state in {"VERIFIED", "QUARANTINED"}:
                return pending.state
            if pending.state == "UNKNOWN":
                return self._reconcile()
            if pending.attempts >= self.max_sends:
                raise ResearchEvaluationSendBudgetExhausted()
            pending = self.journal.begin_send(pending.fingerprint)
            self._target()
            try:
                self.destination.store(pending.envelope)
            except ResearchEvaluationDestinationUnavailable:
                return "UNKNOWN"
            except ResearchEvaluationDestinationConflict:
                return self.journal.quarantine(pending.fingerprint).state
            return self._reconcile()
        finally:
            self._lock.release()
