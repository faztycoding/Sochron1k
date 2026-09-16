from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from .bridge_api import BridgeDep
from .models import StrictModel
from .owner_auth import OwnerAuthDenied, OwnerVerifier
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
