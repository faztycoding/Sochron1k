from __future__ import annotations

import re
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from .alert_lifecycle import (
    AlertLifecycleConflict,
    AlertLifecycleJournal,
    AlertLifecycleUnavailable,
    AlertMutationReceipt,
    enrich_operational_alert_inventory,
    resolution_is_allowed,
)
from .api_budget import ApiBudgetReader, ApiBudgetView
from .bar_history import HistoryUnavailable
from .bridge_api import BridgeDep
from .execution_evidence import (
    ExecutionEvidenceReader,
    ExecutionEvidenceView,
    disabled_execution_evidence,
)
from .models import StrictModel
from .operational_alerts import OperationalAlertInventory, build_operational_alert_inventory
from .owner_auth import OwnerAuthDenied, OwnerVerifier
from .research_statistics import (
    ResearchStatisticsReader,
    ResearchStatisticsUnavailable,
    ResearchStatisticsView,
)
from .signal_evidence import (
    SignalEvidenceReader,
    SignalEvidenceUnavailable,
    SignalEvidenceView,
)
from .telemetry import TelemetryView


async def verified_owner(request: Request) -> UUID:
    verifier: OwnerVerifier = request.app.state.owner_verifier
    try:
        return await verifier.verify(request.headers.getlist("authorization"))
    except OwnerAuthDenied as error:
        raise HTTPException(status_code=error.status, detail=error.code) from None


OwnerDep = Annotated[UUID, Depends(verified_owner)]
router = APIRouter(prefix="/owner", tags=["owner access"])


class OwnerSession(StrictModel):
    authenticated: Literal[True] = True
    owner_id: UUID


@router.get("/session")
def session(owner: OwnerDep) -> OwnerSession:
    return OwnerSession(owner_id=owner)


@router.get("/telemetry")
def telemetry(owner: OwnerDep, bridge: BridgeDep) -> TelemetryView:
    return bridge.view()


@router.get("/execution")
def execution(owner: OwnerDep, request: Request) -> ExecutionEvidenceView:
    reader: ExecutionEvidenceReader | None = request.app.state.execution_evidence
    return reader.view() if reader is not None else disabled_execution_evidence()


def _alert_inventory(request: Request) -> OperationalAlertInventory:
    chart = request.app.state.chart_store
    return build_operational_alert_inventory(
        telemetry=request.app.state.telemetry_bridge,
        execution=request.app.state.execution_bridge,
        journal=request.app.state.execution_evidence,
        history=chart.history,
        policy=request.app.state.policy_writer,
        api_budget=request.app.state.api_budget,
        alert_delivery=request.app.state.alert_delivery_status,
    )


def _idempotency_key(request: Request) -> UUID:
    values = request.headers.getlist("idempotency-key")
    if len(values) != 1 or not re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        values[0] if values else "",
    ):
        raise HTTPException(status_code=400, detail="IDEMPOTENCY_KEY_REQUIRED")
    return UUID(values[0])


def _lifecycle(request: Request) -> AlertLifecycleJournal:
    journal: AlertLifecycleJournal | None = request.app.state.alert_lifecycle
    if journal is None:
        raise HTTPException(status_code=503, detail="ALERT_LIFECYCLE_DISABLED")
    return journal


def _mutation_error(error: Exception) -> HTTPException:
    if isinstance(error, AlertLifecycleConflict):
        return HTTPException(status_code=409, detail=error.code)
    return HTTPException(status_code=503, detail="ALERT_LIFECYCLE_UNAVAILABLE")


def _source_connected(request: Request, source: str) -> bool:
    if source == "telemetry_bridge":
        return request.app.state.telemetry_bridge.view().status.state == "connected"
    if source == "execution_bridge":
        return request.app.state.execution_bridge.status().state == "connected"
    if source == "policy_writer":
        return request.app.state.policy_writer.status().state == "ready"
    if source == "execution_journal":
        reader: ExecutionEvidenceReader | None = request.app.state.execution_evidence
        return reader is not None and reader.operational_facts().state == "available"
    if source == "bar_history":
        history = request.app.state.chart_store.history
        if history is None:
            return False
        try:
            history.storage_status()
        except HistoryUnavailable:
            return False
        return True
    if source == "api_budget":
        budget: ApiBudgetReader = request.app.state.api_budget
        return budget.view().state in {
            "connected", "warning", "critical", "exhausted"
        }
    if source == "alert_delivery":
        return request.app.state.alert_delivery_status.view().state in {
            "connected", "pending"
        }
    return False


@router.get("/alerts")
def alerts(owner: OwnerDep, request: Request) -> OperationalAlertInventory:
    return enrich_operational_alert_inventory(
        _alert_inventory(request), owner, request.app.state.alert_lifecycle
    )


@router.get("/api-budget")
def api_budget(owner: OwnerDep, request: Request) -> ApiBudgetView:
    reader: ApiBudgetReader = request.app.state.api_budget
    return reader.view()


@router.post("/alerts/{condition_id}/acknowledge")
def acknowledge_alert(
    condition_id: str, owner: OwnerDep, request: Request
) -> AlertMutationReceipt:
    if not re.fullmatch(r"[0-9a-f]{24}", condition_id):
        raise HTTPException(status_code=422, detail="INVALID_CONDITION_ID")
    journal = _lifecycle(request)
    key = _idempotency_key(request)
    try:
        replay = journal.replay(owner, "acknowledge", condition_id, key)
        if replay is not None:
            return replay
    except (AlertLifecycleConflict, AlertLifecycleUnavailable) as error:
        raise _mutation_error(error) from None
    inventory = _alert_inventory(request)
    alert = next(
        (item for item in inventory.alerts if item.condition_id == condition_id), None
    )
    if alert is None:
        raise HTTPException(status_code=409, detail="ALERT_NOT_ACTIVE")
    try:
        return journal.acknowledge(owner, alert, key)
    except (AlertLifecycleConflict, AlertLifecycleUnavailable) as error:
        raise _mutation_error(error) from None


@router.post("/alerts/{condition_id}/resolve")
def resolve_alert(
    condition_id: str, owner: OwnerDep, request: Request
) -> AlertMutationReceipt:
    if not re.fullmatch(r"[0-9a-f]{24}", condition_id):
        raise HTTPException(status_code=422, detail="INVALID_CONDITION_ID")
    journal = _lifecycle(request)
    key = _idempotency_key(request)
    try:
        replay = journal.replay(owner, "resolve", condition_id, key)
        if replay is not None:
            return replay
        record = journal.record(owner, condition_id)
        if record is None:
            raise AlertLifecycleConflict("ALERT_NOT_ACKNOWLEDGED")
        inventory = _alert_inventory(request)
        if not resolution_is_allowed(
            inventory,
            record,
            source_connected=_source_connected(request, record.alert.source),
        ):
            raise AlertLifecycleConflict("ALERT_STILL_ACTIVE_OR_SOURCE_INCOMPLETE")
        return journal.resolve(owner, condition_id, key)
    except (AlertLifecycleConflict, AlertLifecycleUnavailable) as error:
        raise _mutation_error(error) from None


@router.get("/signals")
async def signals(owner: OwnerDep, request: Request) -> SignalEvidenceView:
    reader: SignalEvidenceReader | None = request.app.state.signal_evidence
    if reader is None:
        raise HTTPException(status_code=503, detail="SIGNALS_DISABLED")
    try:
        return await reader.view(owner, request.headers.getlist("authorization"))
    except SignalEvidenceUnavailable:
        raise HTTPException(status_code=503, detail="SIGNALS_UNAVAILABLE") from None


@router.get("/statistics")
async def statistics(owner: OwnerDep, request: Request) -> ResearchStatisticsView:
    reader: ResearchStatisticsReader | None = request.app.state.research_statistics
    if reader is None:
        raise HTTPException(status_code=503, detail="STATISTICS_DISABLED")
    try:
        return await reader.view(owner, request.headers.getlist("authorization"))
    except ResearchStatisticsUnavailable:
        raise HTTPException(status_code=503, detail="STATISTICS_UNAVAILABLE") from None
