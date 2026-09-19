"""Redacted UI integration map; never execution or account evidence."""

from __future__ import annotations

from typing import Literal

from .models import StrictModel

ConnectionId = Literal[
    "core_api",
    "owner_auth",
    "market_telemetry",
    "native_chart",
    "bar_history",
    "execution_evidence",
    "signals",
    "statistics",
]
ImplementationState = Literal["available", "partial", "missing"]
RuntimeState = Literal[
    "connected",
    "configured",
    "awaiting_configuration",
    "awaiting_source",
    "degraded",
    "not_applicable",
]


class UiConnection(StrictModel):
    id: ConnectionId
    implementation: ImplementationState
    runtime: RuntimeState
    current_routes: tuple[str, ...] = ()
    required_route: str | None = None
    sources: tuple[str, ...]


class UiConnectionMap(StrictModel):
    demo_only: Literal[True] = True
    auto_trading_enabled: Literal[False] = False
    execution_ready: Literal[False] = False
    connections: tuple[UiConnection, ...]


def _telemetry_runtime(state: str) -> RuntimeState:
    if state == "disabled":
        return "awaiting_configuration"
    if state == "awaiting_snapshot":
        return "awaiting_source"
    if state == "connected":
        return "connected"
    return "degraded"


def _chart_runtime(*, enabled: bool, states: tuple[str, ...]) -> RuntimeState:
    if not enabled or not states or "disabled" in states:
        return "awaiting_configuration"
    if any(state in {"stale", "rejected"} for state in states):
        return "degraded"
    if all(state == "ready" for state in states):
        return "connected"
    return "awaiting_source"


def _execution_runtime(state: str) -> RuntimeState:
    if state == "disabled":
        return "awaiting_configuration"
    if state == "awaiting_inventory":
        return "awaiting_source"
    if state == "connected":
        return "connected"
    return "degraded"


def build_ui_connection_map(
    *,
    owner_auth_configured: bool,
    telemetry_state: str,
    chart_enabled: bool,
    chart_states: tuple[str, ...],
    history_configured: bool,
    execution_state: str,
) -> UiConnectionMap:
    return UiConnectionMap(
        connections=(
            UiConnection(
                id="core_api",
                implementation="available",
                runtime="connected",
                current_routes=("/api/health", "/api/ui/connections"),
                sources=("fastapi",),
            ),
            UiConnection(
                id="owner_auth",
                implementation="available",
                runtime="configured" if owner_auth_configured else "awaiting_configuration",
                current_routes=("/api/auth/config", "/api/owner/session"),
                sources=("supabase_auth",),
            ),
            UiConnection(
                id="market_telemetry",
                implementation="available",
                runtime=_telemetry_runtime(telemetry_state),
                current_routes=("/api/owner/telemetry",),
                sources=("mt5_telemetry",),
            ),
            UiConnection(
                id="native_chart",
                implementation="available",
                runtime=_chart_runtime(enabled=chart_enabled, states=chart_states),
                current_routes=("/api/owner/chart/{timeframe}",),
                sources=("mt5_copyrates",),
            ),
            UiConnection(
                id="bar_history",
                implementation="available",
                runtime="configured" if history_configured else "awaiting_configuration",
                current_routes=("/api/owner/history/{timeframe}",),
                sources=("local_bar_archive",),
            ),
            UiConnection(
                id="execution_evidence",
                implementation="partial",
                runtime=_execution_runtime(execution_state),
                current_routes=("/api/executor/v1/status",),
                required_route="/api/owner/execution",
                sources=("mt5_execution",),
            ),
            UiConnection(
                id="signals",
                implementation="missing",
                runtime="not_applicable",
                required_route="/api/owner/signals",
                sources=("strategy_service",),
            ),
            UiConnection(
                id="statistics",
                implementation="missing",
                runtime="not_applicable",
                required_route="/api/owner/statistics",
                sources=("research_metrics",),
            ),
        )
    )
