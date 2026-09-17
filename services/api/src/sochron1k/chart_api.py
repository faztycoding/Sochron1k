from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from .bridge_api import AuthenticatedBridge, Challenge, bounded_json
from .chart import MAX_CHART_BYTES, PERIODS, ChartFrame, ChartStore, ChartView
from .owner_api import OwnerDep
from .telemetry import BridgeDenied, FrameReceipt


def chart_for(request: Request) -> ChartStore:
    return request.app.state.chart_store


ChartDep = Annotated[ChartStore, Depends(chart_for)]


def authenticated_chart(bridge: AuthenticatedBridge, chart: ChartDep) -> ChartStore:
    if not chart.enabled:
        raise HTTPException(status_code=503, detail="CHART_DISABLED")
    return chart


AuthenticatedChart = Annotated[ChartStore, Depends(authenticated_chart)]
bridge_router = APIRouter(prefix="/bridge/v1/chart", tags=["native chart ingress"])
owner_router = APIRouter(prefix="/owner/chart", tags=["owner chart read"])


@bridge_router.get("/challenge")
def challenge(chart: AuthenticatedChart) -> Challenge:
    return Challenge(boot_id=chart.bridge.boot_id, next_sequence=chart.next_sequence())


@bridge_router.post("/snapshot")
async def receive_chart(request: Request, chart: AuthenticatedChart) -> FrameReceipt:
    decoded = await bounded_json(request, chart.reject, MAX_CHART_BYTES)
    try:
        frame = ChartFrame.model_validate(decoded)
    except ValidationError, ValueError, RecursionError:
        chart.reject()
        raise HTTPException(status_code=422, detail="INVALID_FRAME") from None
    try:
        return chart.accept(frame)
    except BridgeDenied as error:
        raise HTTPException(status_code=409, detail=error.code) from None


@owner_router.get("/{timeframe}")
def chart_window(timeframe: str, owner: OwnerDep, chart: ChartDep) -> ChartView:
    if timeframe not in PERIODS:
        raise HTTPException(status_code=422, detail="INVALID_TIMEFRAME")
    return chart.view(timeframe)
