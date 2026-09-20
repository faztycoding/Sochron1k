"""Redacted owner alert inventory derived from existing read-only evidence."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import AwareDatetime, Field, field_validator

from .bar_history import BarHistory, HistoryUnavailable
from .execution_bridge import ExecutionPollingBridge
from .execution_evidence import ExecutionEvidenceReader
from .models import StrictModel
from .policy_evidence import PolicyEvidenceWriter
from .telemetry import TelemetryBridge

AlertKind = Literal[
    "order_reject",
    "no_sl",
    "risk_halt",
    "unknown_execution",
    "stale_price",
    "bridge_disconnected",
    "storage_limit",
    "api_budget",
]
AlertSource = Literal[
    "telemetry_bridge",
    "execution_bridge",
    "execution_journal",
    "policy_writer",
    "bar_history",
    "api_budget",
]
CoverageRuntime = Literal[
    "connected", "awaiting_configuration", "awaiting_source", "degraded"
]

KINDS: tuple[AlertKind, ...] = (
    "order_reject",
    "no_sl",
    "risk_halt",
    "unknown_execution",
    "stale_price",
    "bridge_disconnected",
    "storage_limit",
    "api_budget",
)
SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


class OperationalAlert(StrictModel):
    id: str = Field(min_length=24, max_length=24, pattern=r"^[0-9a-f]{24}$")
    kind: AlertKind
    severity: Literal["critical", "warning", "info"]
    source: AlertSource
    source_ref: str = Field(min_length=1, max_length=32, pattern=r"^[a-z0-9_-]+$")
    detail_code: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_]+$")
    observed_at_utc: AwareDatetime
    evidence_routes: tuple[str, ...]
    acknowledged_by: None = None
    resolved_at_utc: None = None

    @field_validator("observed_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class AlertCoverage(StrictModel):
    kind: AlertKind
    implementation: Literal["available", "missing"]
    runtime: CoverageRuntime
    api_routes: tuple[str, ...]
    sources: tuple[AlertSource, ...]


class OperationalAlertInventory(StrictModel):
    protocol: Literal["sochron.operational-alerts.v1"] = "sochron.operational-alerts.v1"
    trading_mode: Literal["demo"] = "demo"
    read_only: Literal[True] = True
    auto_trading_enabled: Literal[False] = False
    execution_ready: Literal[False] = False
    delivery_configured: Literal[False] = False
    status: Literal["partial", "degraded"]
    generated_at_utc: AwareDatetime
    truncated: bool = False
    alerts: tuple[OperationalAlert, ...] = ()
    coverage: tuple[AlertCoverage, ...]

    @field_validator("generated_at_utc")
    @classmethod
    def normalize_generated_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


def _alert_id(
    kind: AlertKind, source: AlertSource, source_ref: str, observed: datetime
) -> str:
    payload = "\x1f".join((kind, source, source_ref, observed.astimezone(UTC).isoformat()))
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def _alert(
    *,
    kind: AlertKind,
    severity: Literal["critical", "warning", "info"],
    source: AlertSource,
    source_ref: str,
    detail_code: str,
    observed_at: datetime,
    routes: tuple[str, ...],
) -> OperationalAlert:
    return OperationalAlert(
        id=_alert_id(kind, source, source_ref, observed_at),
        kind=kind,
        severity=severity,
        source=source,
        source_ref=source_ref,
        detail_code=detail_code,
        observed_at_utc=observed_at,
        evidence_routes=routes,
    )


def _telemetry_runtime(state: str) -> CoverageRuntime:
    if state == "disabled":
        return "awaiting_configuration"
    if state == "awaiting_snapshot":
        return "awaiting_source"
    return "connected" if state == "connected" else "degraded"


def _execution_runtime(state: str) -> CoverageRuntime:
    if state == "disabled":
        return "awaiting_configuration"
    if state == "awaiting_inventory":
        return "awaiting_source"
    return "connected" if state == "connected" else "degraded"


def build_operational_alert_inventory(
    *,
    telemetry: TelemetryBridge,
    execution: ExecutionPollingBridge,
    journal: ExecutionEvidenceReader | None,
    history: BarHistory | None,
    policy: PolicyEvidenceWriter,
    now: datetime | None = None,
) -> OperationalAlertInventory:
    generated = (now or datetime.now(UTC)).astimezone(UTC)
    alerts: list[OperationalAlert] = []
    telemetry_view = telemetry.view()
    telemetry_runtime = _telemetry_runtime(telemetry_view.status.state)
    execution_status = execution.status()
    execution_runtime = _execution_runtime(execution_status.state)
    policy_status = policy.status()
    policy_runtime: CoverageRuntime = (
        "awaiting_configuration" if policy_status.state == "disabled"
        else "awaiting_source" if policy_status.state == "awaiting_sources"
        else "connected" if policy_status.state == "ready"
        else "degraded"
    )

    observation_time = (
        telemetry_view.observation.received_time_utc
        if telemetry_view.observation is not None else generated
    )
    if telemetry_view.status.state == "stale":
        alerts.append(_alert(
            kind="stale_price", severity="critical", source="telemetry_bridge",
            source_ref="current", detail_code="price_or_heartbeat_stale",
            observed_at=observation_time, routes=("/api/owner/telemetry",),
        ))
        alerts.append(_alert(
            kind="bridge_disconnected", severity="critical", source="telemetry_bridge",
            source_ref="current", detail_code="telemetry_stale",
            observed_at=observation_time, routes=("/api/owner/telemetry",),
        ))
    elif telemetry_view.status.state == "rejected":
        alerts.append(_alert(
            kind="bridge_disconnected", severity="critical", source="telemetry_bridge",
            source_ref="current", detail_code="telemetry_rejected",
            observed_at=observation_time, routes=("/api/owner/telemetry",),
        ))

    if execution_status.state in {"stale", "rejected"}:
        alerts.append(_alert(
            kind="bridge_disconnected", severity="critical", source="execution_bridge",
            source_ref="current", detail_code=f"execution_{execution_status.state}",
            observed_at=generated, routes=("/api/executor/v1/status",),
        ))
    if policy_status.state == "degraded":
        alerts.append(_alert(
            kind="bridge_disconnected", severity="warning", source="policy_writer",
            source_ref="current", detail_code="policy_writer_degraded",
            observed_at=generated, routes=("/api/policy/v1/status",),
        ))

    journal_runtime: CoverageRuntime = "awaiting_configuration"
    truncated = False
    if journal is not None:
        journal_view = journal.operational_facts()
        journal_runtime = "connected" if journal_view.state == "available" else "degraded"
        truncated = journal_view.truncated
        if journal_view.state == "available":
            severity = {
                "order_reject": "warning",
                "no_sl": "critical",
                "risk_halt": "critical",
                "unknown_execution": "critical",
            }
            for fact in journal_view.facts:
                alerts.append(_alert(
                    kind=fact.kind,
                    severity=severity[fact.kind],
                    source="execution_journal",
                    source_ref=fact.source_ref,
                    detail_code=fact.detail_code,
                    observed_at=fact.observed_at_utc,
                    routes=("/api/owner/execution",),
                ))
        else:
            alerts.append(_alert(
                kind="bridge_disconnected", severity="critical", source="execution_journal",
                source_ref="current", detail_code="execution_journal_unavailable",
                observed_at=generated, routes=("/api/owner/execution",),
            ))

    history_runtime: CoverageRuntime = "awaiting_configuration"
    if history is not None:
        try:
            storage = history.storage_status()
        except HistoryUnavailable:
            history_runtime = "degraded"
            alerts.append(_alert(
                kind="bridge_disconnected", severity="warning", source="bar_history",
                source_ref="current", detail_code="bar_history_unavailable",
                observed_at=generated, routes=("/api/owner/history/{timeframe}",),
            ))
        else:
            history_runtime = "connected"
            if storage.state != "normal":
                alerts.append(_alert(
                    kind="storage_limit", severity="warning", source="bar_history",
                    source_ref="current", detail_code=storage.state,
                    observed_at=generated, routes=("/api/owner/history/{timeframe}",),
                ))

    combined_bridge_runtime: CoverageRuntime = (
        "degraded" if "degraded" in {telemetry_runtime, execution_runtime, policy_runtime}
        else "awaiting_configuration" if "awaiting_configuration" in {
            telemetry_runtime, execution_runtime, policy_runtime
        }
        else "awaiting_source" if "awaiting_source" in {
            telemetry_runtime, execution_runtime, policy_runtime
        }
        else "connected"
    )
    coverage = (
        AlertCoverage(
            kind="order_reject",
            implementation="available",
            runtime=journal_runtime,
            api_routes=("/api/owner/alerts", "/api/owner/execution"),
            sources=("execution_journal",),
        ),
        AlertCoverage(
            kind="no_sl",
            implementation="available",
            runtime=journal_runtime,
            api_routes=("/api/owner/alerts", "/api/owner/execution"),
            sources=("execution_journal",),
        ),
        AlertCoverage(
            kind="risk_halt",
            implementation="available",
            runtime=journal_runtime,
            api_routes=("/api/owner/alerts", "/api/owner/execution"),
            sources=("execution_journal",),
        ),
        AlertCoverage(
            kind="unknown_execution",
            implementation="available",
            runtime=journal_runtime,
            api_routes=("/api/owner/alerts", "/api/owner/execution"),
            sources=("execution_journal",),
        ),
        AlertCoverage(
            kind="stale_price",
            implementation="available",
            runtime=telemetry_runtime,
            api_routes=("/api/owner/alerts", "/api/owner/telemetry"),
            sources=("telemetry_bridge",),
        ),
        AlertCoverage(
            kind="bridge_disconnected",
            implementation="available",
            runtime=combined_bridge_runtime,
            api_routes=(
                "/api/owner/alerts",
                "/api/owner/telemetry",
                "/api/executor/v1/status",
                "/api/policy/v1/status",
            ),
            sources=("telemetry_bridge", "execution_bridge", "policy_writer"),
        ),
        AlertCoverage(
            kind="storage_limit",
            implementation="available",
            runtime=history_runtime,
            api_routes=("/api/owner/alerts", "/api/owner/history/{timeframe}"),
            sources=("bar_history",),
        ),
        AlertCoverage(
            kind="api_budget",
            implementation="missing",
            runtime="awaiting_configuration",
            api_routes=("/api/owner/alerts",),
            sources=("api_budget",),
        ),
    )
    alerts.sort(key=lambda item: (
        SEVERITY_ORDER[item.severity], -item.observed_at_utc.timestamp(), item.kind, item.id
    ))
    degraded = any(item.runtime == "degraded" for item in coverage)
    return OperationalAlertInventory(
        status="degraded" if degraded else "partial",
        generated_at_utc=generated,
        truncated=truncated,
        alerts=tuple(alerts),
        coverage=coverage,
    )
