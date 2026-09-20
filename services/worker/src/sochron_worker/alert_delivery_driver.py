"""One bounded alert-delivery step with receipt reconciliation before retry."""

from __future__ import annotations

import json
from typing import Protocol

from sochron1k.alert_delivery_source import AlertDeliverySourceSnapshot

from .alert_delivery_journal import (
    AlertDeliveryJournal,
    AlertDeliveryReceipt,
    DeliveryIntent,
)


class AlertSourceUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("ALERT_SOURCE_UNAVAILABLE")


class AlertDestinationUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("ALERT_DESTINATION_UNAVAILABLE")


class AlertDestinationConflict(RuntimeError):
    def __init__(self) -> None:
        super().__init__("ALERT_DESTINATION_CONFLICT")


class AlertSendBudgetExhausted(RuntimeError):
    def __init__(self) -> None:
        super().__init__("ALERT_SEND_BUDGET_EXHAUSTED")


class AlertSource(Protocol):
    origin: str

    def read(self) -> AlertDeliverySourceSnapshot: ...


class AlertDestination(Protocol):
    origin: str
    destination_ref: str

    def store(self, intent: DeliveryIntent) -> None: ...

    def read(self, intent: DeliveryIntent) -> AlertDeliveryReceipt | None: ...


class AlertDeliveryDriver:
    def __init__(
        self,
        journal: AlertDeliveryJournal,
        source: AlertSource,
        destination: AlertDestination,
        *,
        max_sends: int,
    ) -> None:
        if type(max_sends) is not int or not 1 <= max_sends <= 5:
            raise ValueError("invalid alert send budget")
        self.journal = journal
        self.source = source
        self.destination = destination
        self.max_sends = max_sends
        self._lock = journal.step_lock

    def _target(self) -> None:
        binding = json.loads(self.journal.binding)
        if (
            self.source.origin != binding["source_origin"]
            or self.destination.origin != binding["destination_origin"]
            or self.destination.destination_ref != binding["destination_ref"]
        ):
            raise AlertDestinationConflict()

    def _reconcile(self, pending: DeliveryIntent) -> str:
        self._target()
        try:
            receipt = self.destination.read(pending)
        except AlertDestinationUnavailable:
            return "UNKNOWN"
        except AlertDestinationConflict:
            return self.journal.quarantine(pending.delivery_id).state
        return self.journal.reconcile(pending.delivery_id, receipt).state

    def reconcile_pending(self) -> str:
        """Read the receiver only; never fetch, prepare or send."""
        if not self._lock.acquire(blocking=False):
            raise AlertDestinationUnavailable()
        try:
            self._target()
            state = self.journal.status()
            if state.quarantined:
                return "QUARANTINED"
            pending = state.pending
            if pending is None:
                return "NO_PENDING"
            if pending.state == "PREPARED":
                return "REVIEW_REQUIRED"
            return self._reconcile(pending)
        finally:
            self._lock.release()

    def step(self) -> str:
        if not self._lock.acquire(blocking=False):
            raise AlertDestinationUnavailable()
        try:
            self._target()
            state = self.journal.status()
            if state.quarantined:
                return "QUARANTINED"
            pending = state.pending
            if pending is None:
                snapshot = self.source.read()
                if snapshot.truncated:
                    raise AlertSourceUnavailable()
                for fact in snapshot.alerts:
                    candidate = self.journal.prepare(fact)
                    if candidate is not None and candidate.state in {"PREPARED", "UNKNOWN"}:
                        pending = candidate
                        break
                if pending is None:
                    return "IDLE"
            if pending.state == "UNKNOWN":
                return self._reconcile(pending)
            if pending.attempts >= self.max_sends:
                raise AlertSendBudgetExhausted()
            pending = self.journal.begin_send(pending.delivery_id)
            self._target()
            try:
                self.destination.store(pending)
            except AlertDestinationUnavailable:
                return "UNKNOWN"
            except AlertDestinationConflict:
                return self.journal.quarantine(pending.delivery_id).state
            return self._reconcile(pending)
        finally:
            self._lock.release()
