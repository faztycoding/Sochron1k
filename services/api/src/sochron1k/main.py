from __future__ import annotations

import os
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from . import __version__


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    trading_mode: Literal["demo"]
    auto_trading_enabled: bool
    execution_ready: bool


def create_app() -> FastAPI:
    app = FastAPI(title="Sochron1k API", version=__version__)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        mode = os.environ.get("TRADING_MODE", "demo")
        auto_enabled = os.environ.get("AUTO_TRADING_ENABLED", "false").lower() == "true"
        if mode != "demo":
            auto_enabled = False
        return HealthResponse(
            status="ok",
            service="sochron1k-api",
            version=__version__,
            trading_mode="demo",
            auto_trading_enabled=auto_enabled,
            execution_ready=False,
        )

    return app


app = create_app()
