from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from starlette.requests import ClientDisconnect

from .models import StrictModel
from .telemetry import (
    MAX_FRAME_BYTES,
    BridgeDenied,
    BridgeStatus,
    FrameReceipt,
    Observation,
    TelemetryBridge,
    TelemetryFrame,
)


class Challenge(StrictModel):
    boot_id: UUID
    next_sequence: int


def bridge_for(request: Request) -> TelemetryBridge:
    return request.app.state.telemetry_bridge


BridgeDep = Annotated[TelemetryBridge, Depends(bridge_for)]


def authenticated_bridge(request: Request, bridge: BridgeDep) -> TelemetryBridge:
    if bridge.settings is None:
        raise HTTPException(status_code=503, detail="BRIDGE_DISABLED")
    if not bridge.authenticate(request.headers.getlist("authorization")):
        raise HTTPException(
            status_code=401, detail="BRIDGE_UNAUTHORIZED", headers={"WWW-Authenticate": "Bearer"}
        )
    return bridge


AuthenticatedBridge = Annotated[TelemetryBridge, Depends(authenticated_bridge)]
router = APIRouter(prefix="/bridge/v1", tags=["read-only telemetry"])


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("ambiguous JSON")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON")


@router.get("/status")
def status(bridge: BridgeDep) -> BridgeStatus:
    return bridge.status()


@router.get("/challenge")
def challenge(bridge: AuthenticatedBridge) -> Challenge:
    last = bridge.observation()
    return Challenge(boot_id=bridge.boot_id, next_sequence=last.frame.sequence + 1 if last else 1)


@router.get("/snapshot")
def snapshot(bridge: AuthenticatedBridge) -> Observation:
    observation = bridge.observation()
    if observation is None:
        raise HTTPException(status_code=404, detail="NO_OBSERVATION")
    # This is the last observation, NOT a freshness or execution-readiness claim.
    return observation


async def bounded_json(request: Request, reject: Callable[[], None], max_bytes: int) -> object:
    """Called only after the route's authentication dependency has succeeded."""

    def deny(status_code: int, code: str) -> None:
        reject()
        raise HTTPException(status_code=status_code, detail=code)

    if request.headers.get("content-type", "").split(";", 1)[0].strip() != "application/json":
        deny(415, "JSON_REQUIRED")
    if request.headers.get("content-encoding", "identity") != "identity":
        deny(415, "ENCODING_NOT_SUPPORTED")
    body = bytearray()
    try:
        async with asyncio.timeout(2):
            async for chunk in request.stream():
                if len(body) + len(chunk) > max_bytes:
                    deny(413, "FRAME_TOO_LARGE")
                body.extend(chunk)
    except TimeoutError:
        deny(408, "FRAME_TIMEOUT")
    except ClientDisconnect:
        deny(400, "FRAME_INTERRUPTED")
    try:
        return json.loads(
            body,
            object_pairs_hook=unique_object,
            parse_float=Decimal,
            parse_constant=reject_constant,
        )
    except ValueError, RecursionError:
        deny(422, "INVALID_FRAME")


@router.post("/snapshot")
async def receive_snapshot(request: Request, bridge: AuthenticatedBridge) -> FrameReceipt:
    decoded = await bounded_json(request, bridge.reject, MAX_FRAME_BYTES)
    try:
        frame = TelemetryFrame.model_validate(decoded)
    except ValidationError, ValueError, RecursionError:
        # Pydantic's default errors include input values; do not echo broker data.
        bridge.reject()
        raise HTTPException(status_code=422, detail="INVALID_FRAME") from None
    try:
        return bridge.accept(frame)
    except BridgeDenied as error:
        raise HTTPException(status_code=409, detail=error.code) from None
