from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from pydantic import BaseModel

from . import __version__
from .bar_history import BarHistory, HistoryUnavailable
from .bridge_api import router as bridge_router
from .chart import ChartSettings, ChartStore, load_chart_settings
from .chart_api import bridge_router as chart_bridge_router
from .chart_api import history_router
from .chart_api import owner_router as chart_owner_router
from .owner_api import router as owner_router
from .owner_auth import OwnerAuthSettings, OwnerVerifier, load_owner_auth_settings
from .telemetry import BridgeSettings, TelemetryBridge, load_bridge_settings


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    trading_mode: Literal["demo"]
    auto_trading_enabled: bool
    execution_ready: bool


class PublicAuthConfig(BaseModel):
    enabled: bool
    supabase_url: str | None = None
    public_key: str | None = None


def create_app(
    bridge_settings: BridgeSettings | None = None,
    owner_auth_settings: OwnerAuthSettings | None = None,
    chart_settings: ChartSettings | None = None,
    history_directory: Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Sochron1k API", version=__version__)
    app.state.telemetry_bridge = TelemetryBridge(bridge_settings)
    app.state.owner_verifier = OwnerVerifier(owner_auth_settings)
    history = None
    if history_directory is not None:
        if bridge_settings is None or chart_settings is None:
            raise HistoryUnavailable()
        history = BarHistory(history_directory, bridge_settings, chart_settings)
    app.state.chart_store = ChartStore(app.state.telemetry_bridge, chart_settings, history=history)
    app.include_router(bridge_router)
    app.include_router(owner_router)
    app.include_router(chart_bridge_router)
    app.include_router(chart_owner_router)
    app.include_router(history_router)

    @app.middleware("http")
    async def bridge_no_cache(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(("/bridge/", "/owner/", "/auth/")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/auth/config", response_model_exclude_none=True)
    def auth_config() -> PublicAuthConfig:
        if owner_auth_settings is None:
            return PublicAuthConfig(enabled=False)
        return PublicAuthConfig(
            enabled=True,
            supabase_url=owner_auth_settings.supabase_url,
            public_key=owner_auth_settings.public_key.get_secret_value(),
        )

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


app = create_app(
    load_bridge_settings(),
    load_owner_auth_settings(),
    load_chart_settings(),
    Path(os.environ["SOCHRON_CHART_HISTORY_DIR"])
    if os.environ.get("SOCHRON_CHART_HISTORY_DIR")
    else None,
)
