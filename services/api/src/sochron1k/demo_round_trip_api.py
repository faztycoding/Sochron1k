from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request

from .demo_round_trip import (
    DemoRoundTripController,
    DemoRoundTripDenied,
    DemoRoundTripManagementRequest,
    DemoRoundTripOpenRequest,
    DemoRoundTripStatus,
    RiskBaselineReceipt,
    StartupReceipt,
    disabled_demo_round_trip_status,
)
from .models import SubmissionResult


def controller_for(request: Request) -> DemoRoundTripController:
    controller: DemoRoundTripController | None = request.app.state.demo_round_trip
    if controller is None:
        raise HTTPException(status_code=503, detail="DEMO_ROUND_TRIP_DISABLED")
    return controller


ControllerDep = Annotated[DemoRoundTripController, Depends(controller_for)]


def authenticated_controller(
    request: Request, controller: ControllerDep
) -> DemoRoundTripController:
    if not controller.authenticate(request.headers.getlist("authorization")):
        raise HTTPException(
            status_code=401,
            detail="DEMO_ROUND_TRIP_UNAUTHORIZED",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return controller


AuthenticatedController = Annotated[DemoRoundTripController, Depends(authenticated_controller)]
router = APIRouter(prefix="/internal/v1/demo-round-trip", tags=["bounded Demo round trip"])


def _run(call):
    try:
        return call()
    except DemoRoundTripDenied as error:
        raise HTTPException(
            status_code=503 if error.unavailable else 409,
            detail=error.code,
        ) from None


@router.get("/status")
def status(request: Request) -> DemoRoundTripStatus:
    controller: DemoRoundTripController | None = request.app.state.demo_round_trip
    return controller.status() if controller is not None else disabled_demo_round_trip_status()


@router.post("/risk-baseline")
def risk_baseline(controller: AuthenticatedController) -> RiskBaselineReceipt:
    return _run(controller.initialize_risk_baseline)


@router.post("/startup")
def startup(controller: AuthenticatedController) -> StartupReceipt:
    return _run(controller.startup)


@router.post("/open")
def open_entry(
    request: DemoRoundTripOpenRequest,
    controller: AuthenticatedController,
) -> SubmissionResult:
    return _run(lambda: controller.open(request))


@router.post("/{operation}")
def manage(
    operation: Literal["cancel", "close"],
    request: DemoRoundTripManagementRequest,
    controller: AuthenticatedController,
) -> SubmissionResult:
    from .models import ManagementOperation

    return _run(lambda: controller.manage(request, ManagementOperation(operation)))


@router.post("/reconcile/{command_id}")
def reconcile(command_id: str, controller: AuthenticatedController) -> SubmissionResult:
    if not command_id or len(command_id) > 128:
        raise HTTPException(status_code=422, detail="INVALID_COMMAND_ID")
    return _run(lambda: controller.reconcile(command_id))
