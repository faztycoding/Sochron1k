from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import ValidationError

from .bridge_api import bounded_json
from .execution_bridge import (
    MAX_EXECUTION_FRAME_BYTES,
    ExecutionBridgeChallenge,
    ExecutionBridgeDenied,
    ExecutionBridgeReceipt,
    ExecutionBridgeStatus,
    ExecutionDispatch,
    ExecutionInventoryFrame,
    ExecutionOutcomeFrame,
    ExecutionPollingBridge,
)


def execution_bridge_for(request: Request) -> ExecutionPollingBridge:
    return request.app.state.execution_bridge


ExecutionBridgeDep = Annotated[ExecutionPollingBridge, Depends(execution_bridge_for)]


def authenticated_execution_bridge(
    request: Request, bridge: ExecutionBridgeDep
) -> ExecutionPollingBridge:
    if bridge.settings is None:
        raise HTTPException(status_code=503, detail="EXECUTION_BRIDGE_DISABLED")
    if not bridge.authenticate(request.headers.getlist("authorization")):
        raise HTTPException(
            status_code=401,
            detail="EXECUTION_BRIDGE_UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return bridge


AuthenticatedExecutionBridge = Annotated[
    ExecutionPollingBridge, Depends(authenticated_execution_bridge)
]
router = APIRouter(prefix="/executor/v1", tags=["internal Demo executor"])


@router.get("/status")
def status(bridge: ExecutionBridgeDep) -> ExecutionBridgeStatus:
    return bridge.status()


@router.get("/challenge")
def challenge(bridge: AuthenticatedExecutionBridge) -> ExecutionBridgeChallenge:
    return bridge.challenge()


@router.post("/inventory")
async def receive_inventory(
    request: Request,
    background_tasks: BackgroundTasks,
    bridge: AuthenticatedExecutionBridge,
) -> ExecutionBridgeReceipt:
    decoded = await bounded_json(request, bridge.reject, MAX_EXECUTION_FRAME_BYTES)
    try:
        frame = ExecutionInventoryFrame.model_validate(decoded)
    except ValidationError, ValueError, RecursionError:
        bridge.reject()
        raise HTTPException(status_code=422, detail="INVALID_EXECUTOR_FRAME") from None
    try:
        receipt = bridge.accept_inventory(frame)
    except ExecutionBridgeDenied as error:
        raise HTTPException(status_code=409, detail=error.code) from None
    background_tasks.add_task(
        request.app.state.policy_writer.refresh,
        request.app.state.telemetry_bridge,
        bridge,
    )
    return receipt


@router.get("/commands/next", response_model=ExecutionDispatch | None)
def next_command(bridge: AuthenticatedExecutionBridge) -> ExecutionDispatch | Response:
    command = bridge.next_command()
    return command if command is not None else Response(status_code=204)


@router.post("/outcomes")
async def receive_outcome(
    request: Request, bridge: AuthenticatedExecutionBridge
) -> ExecutionBridgeReceipt:
    decoded = await bounded_json(request, bridge.reject, MAX_EXECUTION_FRAME_BYTES)
    try:
        frame = ExecutionOutcomeFrame.model_validate(decoded)
    except ValidationError, ValueError, RecursionError:
        bridge.reject()
        raise HTTPException(status_code=422, detail="INVALID_EXECUTOR_FRAME") from None
    try:
        return bridge.accept_outcome(frame)
    except ExecutionBridgeDenied as error:
        raise HTTPException(status_code=409, detail=error.code) from None
