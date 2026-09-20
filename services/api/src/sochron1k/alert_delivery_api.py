"""Private service route for the alert delivery worker; never browser auth."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from .alert_delivery_source import (
    AlertDeliverySourceSnapshot,
    AlertSourceAuthenticator,
    delivery_source_snapshot,
)
from .operational_alerts import build_operational_alert_inventory


def authenticated_alert_source(request: Request) -> AlertSourceAuthenticator:
    authenticator: AlertSourceAuthenticator = request.app.state.alert_source_authenticator
    if authenticator.settings is None:
        raise HTTPException(status_code=503, detail="ALERT_SOURCE_DISABLED")
    if not authenticator.authenticate(request.headers.getlist("authorization")):
        raise HTTPException(
            status_code=401,
            detail="ALERT_SOURCE_UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authenticator


AlertSourceDep = Annotated[AlertSourceAuthenticator, Depends(authenticated_alert_source)]
router = APIRouter(prefix="/internal/v1", tags=["private alert delivery source"])


@router.get("/alerts")
def current_alerts(request: Request, source: AlertSourceDep) -> AlertDeliverySourceSnapshot:
    del source
    chart = request.app.state.chart_store
    inventory = build_operational_alert_inventory(
        telemetry=request.app.state.telemetry_bridge,
        execution=request.app.state.execution_bridge,
        journal=request.app.state.execution_evidence,
        history=chart.history,
        policy=request.app.state.policy_writer,
        api_budget=request.app.state.api_budget,
        alert_delivery=request.app.state.alert_delivery_status,
    )
    return delivery_source_snapshot(inventory)
