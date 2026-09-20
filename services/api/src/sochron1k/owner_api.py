from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

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
router = APIRouter(prefix="/owner", tags=["owner read access"])


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


@router.get("/alerts")
def alerts(owner: OwnerDep, request: Request) -> OperationalAlertInventory:
    chart = request.app.state.chart_store
    return build_operational_alert_inventory(
        telemetry=request.app.state.telemetry_bridge,
        execution=request.app.state.execution_bridge,
        journal=request.app.state.execution_evidence,
        history=chart.history,
        policy=request.app.state.policy_writer,
    )


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
