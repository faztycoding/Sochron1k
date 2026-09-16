from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, Request
from pydantic import BaseModel

from . import __version__
from .bridge_api import router as bridge_router
from .telemetry import BridgeSettings, TelemetryBridge, load_bridge_settings


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    trading_mode: Literal["demo"]
    auto_trading_enabled: bool
    execution_ready: bool


def create_app(bridge_settings: BridgeSettings | None = None) -> FastAPI:
    app = FastAPI(title="Sochron1k API", version=__version__)
    app.state.telemetry_bridge = TelemetryBridge(bridge_settings)
    app.include_router(bridge_router)

    @app.middleware("http")
    async def bridge_no_cache(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/bridge/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="sochron1k-api",
            version=__version__,
            trading_mode="demo",
            auto_trading_enabled=False,
            execution_ready=False,
        )

    return app


app = create_app(load_bridge_settings())
