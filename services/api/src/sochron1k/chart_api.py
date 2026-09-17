from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from .bar_history import HistoryUnavailable, HistoryView
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
history_router = APIRouter(prefix="/owner/history", tags=["owner closed-bar history"])


@bridge_router.get("/challenge")
def challenge(chart: AuthenticatedChart) -> Challenge:
    return Challenge(boot_id=chart.bridge.boot_id, next_sequence=chart.next_sequence())


@bridge_router.post("/snapshot")
async def receive_chart(request: Request, chart: AuthenticatedChart) -> FrameReceipt:
    try:
        decoded = await bounded_json(request, lambda: None, MAX_CHART_BYTES)
    except HTTPException:
        await run_in_threadpool(chart.reject)
        raise
    try:
        frame = ChartFrame.model_validate(decoded)
    except ValidationError, ValueError, RecursionError:
        await run_in_threadpool(chart.reject)
        raise HTTPException(status_code=422, detail="INVALID_FRAME") from None
    try:
        return await run_in_threadpool(chart.accept, frame)
    except HistoryUnavailable:
        raise HTTPException(status_code=503, detail="HISTORY_UNAVAILABLE") from None
    except BridgeDenied as error:
        raise HTTPException(status_code=409, detail=error.code) from None


@owner_router.get("/{timeframe}")
def chart_window(timeframe: str, owner: OwnerDep, chart: ChartDep) -> ChartView:
    if timeframe not in PERIODS:
        raise HTTPException(status_code=422, detail="INVALID_TIMEFRAME")
    return chart.view(timeframe)


@history_router.get("/{timeframe}")
def history_window(
    timeframe: str,
    owner: OwnerDep,
    chart: ChartDep,
    after_server_s: Annotated[int, Query(ge=0, le=4_102_444_800)] = 0,
    through_receipt: Annotated[int | None, Query(ge=0, le=9_007_199_254_740_991)] = None,
    archive_id: Annotated[str | None, Query(max_length=36)] = None,
    limit: Annotated[int, Query(ge=1, le=240)] = 240,
) -> HistoryView:
    if timeframe not in PERIODS:
        raise HTTPException(status_code=422, detail="INVALID_TIMEFRAME")
    if chart.history is None:
        return HistoryView(state="disabled", timeframe=timeframe)
    try:
        return chart.history.read(
            timeframe,
            after_server_s=after_server_s,
            through_receipt=through_receipt,
            archive_id=archive_id,
            limit=limit,
        )
    except HistoryUnavailable:
        chart.fail_history()
        raise HTTPException(status_code=503, detail="HISTORY_UNAVAILABLE") from None
    except BridgeDenied as error:
        raise HTTPException(status_code=409, detail=error.code) from None
