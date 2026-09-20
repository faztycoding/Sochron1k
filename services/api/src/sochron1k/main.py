from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from pydantic import BaseModel

from . import __version__
from .alert_lifecycle import AlertLifecycleJournal, load_alert_lifecycle_journal
from .bar_history import BarHistory, HistoryUnavailable
from .bridge_api import router as bridge_router
from .chart import ChartSettings, ChartStore, load_chart_settings
from .chart_api import bridge_router as chart_bridge_router
from .chart_api import history_router
from .chart_api import owner_router as chart_owner_router
from .demo_readiness import (
    DemoOwnerDecisions,
    DemoReadiness,
    build_demo_readiness,
    load_demo_owner_decisions,
)
from .execution_bridge import (
    ExecutionBridgeSettings,
    ExecutionPollingBridge,
    load_execution_bridge_settings,
)
from .execution_bridge_api import router as execution_bridge_router
from .execution_evidence import ExecutionEvidenceReader, load_execution_evidence_reader
from .owner_api import router as owner_router
from .owner_auth import OwnerAuthSettings, OwnerVerifier, load_owner_auth_settings
from .policy_api import router as policy_router
from .policy_evidence import (
    PolicyEvidenceWriter,
    PolicyWriterSettings,
    load_policy_writer_settings,
)
from .research_statistics import ResearchStatisticsReader
from .signal_evidence import SignalEvidenceReader
from .telemetry import BridgeSettings, TelemetryBridge, load_bridge_settings
from .ui_connections import UiConnectionMap, build_ui_connection_map


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
    execution_bridge_settings: ExecutionBridgeSettings | None = None,
    execution_evidence: ExecutionEvidenceReader | None = None,
    signal_evidence: SignalEvidenceReader | None = None,
    research_statistics: ResearchStatisticsReader | None = None,
    policy_writer_settings: PolicyWriterSettings | None = None,
    demo_owner_decisions: DemoOwnerDecisions | None = None,
    alert_lifecycle: AlertLifecycleJournal | None = None,
) -> FastAPI:
    if (
        bridge_settings is not None
        and execution_bridge_settings is not None
        and bridge_settings.token.get_secret_value()
        == execution_bridge_settings.token.get_secret_value()
    ):
        raise RuntimeError("telemetry and execution bridges require separate credentials")
    if policy_writer_settings is not None and (
        bridge_settings is None
        or execution_bridge_settings is None
        or bridge_settings.identity != policy_writer_settings.identity
        or execution_bridge_settings.identity != policy_writer_settings.identity
    ):
        raise RuntimeError("policy writer requires matching telemetry and execution identities")
    app = FastAPI(title="Sochron1k API", version=__version__)
    app.state.telemetry_bridge = TelemetryBridge(bridge_settings)
    app.state.execution_bridge = ExecutionPollingBridge(execution_bridge_settings)
    app.state.policy_writer = PolicyEvidenceWriter(policy_writer_settings)
    app.state.owner_verifier = OwnerVerifier(owner_auth_settings)
    app.state.execution_evidence = execution_evidence
    app.state.alert_lifecycle = alert_lifecycle
    app.state.signal_evidence = signal_evidence or (
        SignalEvidenceReader(owner_auth_settings) if owner_auth_settings is not None else None
    )
    app.state.research_statistics = research_statistics or (
        ResearchStatisticsReader(owner_auth_settings) if owner_auth_settings is not None else None
    )
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
    app.include_router(execution_bridge_router)
    app.include_router(policy_router)

    @app.middleware("http")
    async def bridge_no_cache(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith(
            ("/bridge/", "/executor/", "/owner/", "/auth/", "/ui/", "/policy/")
        ):
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

    @app.get("/ui/connections")
    def ui_connections() -> UiConnectionMap:
        chart = app.state.chart_store
        chart_states = tuple(chart.view(timeframe).state for timeframe in ("M1", "M5", "M15", "H1"))
        return build_ui_connection_map(
            owner_auth_configured=owner_auth_settings is not None,
            telemetry_state=app.state.telemetry_bridge.status().state,
            chart_enabled=chart.enabled,
            chart_states=chart_states,
            history_configured=chart.history is not None,
            execution_state=app.state.execution_bridge.status().state,
            execution_evidence_state=(
                execution_evidence.runtime_state()
                if execution_evidence is not None
                else "awaiting_configuration"
            ),
            signal_configured=app.state.signal_evidence is not None,
            policy_state=app.state.policy_writer.status().state,
            statistics_configured=app.state.research_statistics is not None,
        )

    @app.get("/ui/demo-readiness")
    def ui_demo_readiness() -> DemoReadiness:
        chart = app.state.chart_store
        chart_states = tuple(chart.view(timeframe).state for timeframe in ("M1", "M5", "M15", "H1"))
        return build_demo_readiness(
            owner_decisions_recorded=demo_owner_decisions is not None,
            owner_auth_configured=owner_auth_settings is not None,
            telemetry_state=app.state.telemetry_bridge.status().state,
            chart_enabled=chart.enabled,
            chart_states=chart_states,
            history_configured=chart.history is not None,
            execution_state=app.state.execution_bridge.status().state,
            execution_evidence_state=(
                execution_evidence.runtime_state()
                if execution_evidence is not None
                else "awaiting_configuration"
            ),
            signal_configured=app.state.signal_evidence is not None,
            policy_state=app.state.policy_writer.status().state,
            statistics_configured=app.state.research_statistics is not None,
        )

    return app


app = create_app(
    load_bridge_settings(),
    load_owner_auth_settings(),
    load_chart_settings(),
    Path(os.environ["SOCHRON_CHART_HISTORY_DIR"])
    if os.environ.get("SOCHRON_CHART_HISTORY_DIR")
    else None,
    load_execution_bridge_settings(),
    load_execution_evidence_reader(),
    policy_writer_settings=load_policy_writer_settings(),
    demo_owner_decisions=load_demo_owner_decisions(),
    alert_lifecycle=load_alert_lifecycle_journal(),
)
